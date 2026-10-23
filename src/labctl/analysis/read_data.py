"""Data loading and reshaping helpers for SIF camera acquisitions."""
import pathlib
import pickle
import warnings
from collections.abc import Callable, Collection, Iterable
from typing import Any, Literal, NotRequired, TypedDict, Unpack, cast
import math

import numpy as np
import sif_parser

from labctl._type_hints import (
    _acc_typehint,
    _file_path_or_collection_type,
    _file_path_type,
)
from labctl.analysis._numpy_funcs import _get_accumulator
from labctl.analysis import CombinedMeasurement, Measurement
from labctl.experiments import BackgroundConfiguration


class GetDataKwargs(TypedDict):
    width_indexes: NotRequired[tuple[float, float]]
    height_indexes: NotRequired[tuple[int, int]]
    config_flattener: NotRequired[_acc_typehint]
    height_flattener: NotRequired[_acc_typehint]
    as_list: NotRequired[bool]
    no_pickle: NotRequired[bool]


class GetDataGluedKwargs(GetDataKwargs):
    remove_overlap: NotRequired[bool]
    include_background: NotRequired[bool | Literal['auto']]
    intensity_factors: NotRequired[Collection[float]]


def _config_num(info: dict[str, Any]) -> int:
    """
    Return the number of experiment configuration steps based on 'n_frames' stored in *info*.

    Parameters
    ----------
    info : dict
        Experiment metadata dictionary

    Returns
    -------
    int
        Number of configuration steps.

    Raises
    ------
    ValueError
        If the ``'variable'`` key is absent from *info*.
    """
    if "n_frames" in info:
        return len(info["n_frames"])
    else:
        raise ValueError("No 'N_frames' key found in info, cannot extract experiment variable(s).")


def _check_indexes(
    given_value: tuple[float, float] | None,
    dir_image_size: int,
    name: str,
) -> tuple[float, float]:
    """
    Validate and normalise a pixel-range crop specification.

    Parameters
    ----------
    given_value : tuple[int, int] | None
        Requested ``(start, stop)`` range, or ``None`` for the full
        extent along this axis.
    dir_image_size : int
        Total number of pixels along this axis.
    name : str
        Axis name used in error messages (e.g. ``'width'``).

    Returns
    -------
    tuple[float, float]
        Validated ``(start, stop)`` pixel range.

    Raises
    ------
    ValueError
        If the range is empty, starts below zero, or exceeds the image
        dimension.
    """
    if given_value is None:
        return 0, dir_image_size
    if len(given_value) != 2:
        msg = f"`{name}_indexes` should have length 2, found {len(given_value)}"
        raise ValueError(msg)

    if given_value[1] < 0:
        given_value = (given_value[0], given_value[1] % dir_image_size)

    if given_value[0] >= given_value[1]:
        msg = f"For `{name}_indexes` first value should be smaller than second value, found {given_value}"
    elif given_value[0] < 0:
        msg = f"For `{name}_indexes` first value should be bigger or equal to zero, found {given_value[0]}"
    elif given_value[1] > dir_image_size:
        msg = (f"For `{name}_indexes` second value should be smaller or equal to image size ({dir_image_size}), "
               f"found {given_value[0]}")
    else:
        return given_value[0], given_value[1]
    raise ValueError(msg)


def _check_width_indexes(width_indexes: tuple[float, float] | None, img_width: int, wavelengths: np.ndarray) -> tuple[int, int]:
    width_indexes = _check_indexes(width_indexes, img_width, 'width_indexes')

    if isinstance(width_indexes[0], int) and isinstance(width_indexes[1], int):
        return width_indexes

    return tuple(np.searchsorted(wavelengths, width_indexes))


def _check_height_indexes(height_indexes: tuple[int, int] | None, img_height: int) -> tuple[int, int]:
    new_height_indexes = _check_indexes(height_indexes, img_height, 'height_indexes')

    for i in range(2):
        if not isinstance(new_height_indexes[i], int):
            msg = f"`height_indexes` should be two integers, found {type(new_height_indexes[i]).__name__} at index {i}."
            raise TypeError(msg)
    return new_height_indexes

def _flatten_iter(value: Iterable, /, *, max_dept=math.inf) -> Iterable:
    """
    Flatten an arbitrary depth iterator.

    Parameters
    ----------
    value : Iterable
        The iterable to flatten.
    max_dept : int, optional
        The maximum depth to flatten. Defaults to infinity, meaning it will flatten all levels.
    """
    if max_dept < 0:
        yield value
        return

    for item in value:
        if isinstance(item, Iterable):
            yield from _flatten_iter(item, max_dept=max_dept - 1)
        else:
            yield item


def get_data(
    sif_loc: _file_path_type,
    pickle_loc: _file_path_type,
    *,
    width_indexes: tuple[float, float] | None = None,
    height_indexes: tuple[int, int] | None = None,
    config_flattener: _acc_typehint | None = None,
    height_flattener: _acc_typehint | None = None,
    as_list: bool = False,
    no_pickle: bool = False,
) -> Measurement:
    """
    Load and reshape experiment image data from a SIF file and its companion
    pickle metadata file.

    Parameters
    ----------
    sif_loc : str | PathLike[str]
        Path to the Andor SIF image file.
    pickle_loc : str | PathLike[str]
        Path to the pickle file containing experiment metadata (frame
        indices, sweep variable values, background configuration, etc.).
    width_indexes : tuple[int, int] | tuple[float, float] | None, optional
        ``(start, stop)`` pixel crop along the width axis.  ``None`` uses
        the full width. If a tuple of floats is provided, it is interpreted as a wavelength range and converted to
        pixel indices using the SIF file's wavelength calibration.
    height_indexes : tuple[int, int] | None, optional
        ``(start, stop)`` pixel crop along the height axis.  ``None`` uses
        the full height.
    config_flattener : _acc_typehint | None, optional
        How to collapse measurements at the same configuration into a single measurement.

        * ``None`` – keep every frame individually; all configurations must
          have the same number of frames.
        * ``'median'``, ``'mean'``, or ``'sum'`` – apply the named NumPy
          reduction over the frame axis (axis ``-3``).
        * A callable that performs a custom reduction over axis ``-3``.
    height_flattener: _acc_typehint | None, optional
        How to collapse the height axis into a single value per pixel column.
        Same options as *iter_accumulator*, but applied along axis ``-2``.
    as_list: bool, optional
        If value is ``True``, the ``n_iter`` (if present) and ``config_num`` axis are lists instead of ``np.ndarray``,
        useful when the number of frames per configurations is not the same (so a numpy array is not possible).
    no_pickle: bool
        If you have a measurement without a pickle file, set this to ``True``. The shape of data is then implied from
        the sif file.

    Returns
    -------
    Measurement
        An instance of the Measurement class.

        * Without *config_flattener* or *height_flattener* the arrays have shape
          ``(config_num, n_frames, height, width)``.
        * With an *config_flattener* the frame dimension is collapsed:
          ``(config_num, height, width)``.
        * With *height_flattener* the height dimension is collapsed:
          ``(config_num, n_frames, width)``.
        * With both *config_flattener* and *height_flattener* the shape is
          ``(config_num, width)``.
        * When the experiment contains multiple iterations an extra leading
          axis is prepended: ``(n_iter, config_num, ...)``.
        * *background* is ``None`` when no background frames were recorded
          (``background_every == 0``).
        * If as_list is True, the ``n_iter`` (if present) and ``config_num`` axis are lists,
          measurements are still numpy arrays.

    Raises
    ------
    ValueError
        If any index crop is out of range, or if *config_flattener* is
        ``None`` and configurations have differing numbers of frames.

    Notes
    -----
    The `config_flattener` is applied before the `height_flattener`
    """
    pickle_loc = pathlib.Path(pickle_loc)
    sif_loc = pathlib.Path(sif_loc)
    if pickle_loc.suffix == '.sif' and sif_loc.suffix == '.pkl':
        warnings.warn("You put the `sif_loc` and `pickle_loc` the wrong way around.")

    img_data, img_info = sif_parser.np_open(sif_loc)
    image_size = img_info['size']
    if no_pickle:
        info = {
            "background_every": 0,
            "n_iter": 1,
            "n_frames": [img_data.shape[0]],
            "indices_full": [[[[i for i in range(img_data.shape[0])]], [[]]]]
        }
    else:
        info = get_info(pickle_loc)
        if "version" not in info:
            raise ValueError("Only labctl pickle files generated by version 0.0.2 and newer are supported, not 0.0.1")

    pickle_frame_num = len(list(_flatten_iter(info["indices_full"])))
    if pickle_frame_num != img_data.shape[0]:
        msg = f"The pickle file ({pickle_frame_num}) has a different number of frames than the sif file ({img_data.shape[0]})"
        raise ValueError(msg)

    has_background = info["background_every"] != 0
    config_num = _config_num(info)

    wavelengths = _get_wavelengths(img_info)

    width_indexes_out = _check_width_indexes(width_indexes, image_size[0], wavelengths)
    height_indexes_out = _check_height_indexes(height_indexes, image_size[1])
    new_image_size = (height_indexes_out[1]-height_indexes_out[0], width_indexes_out[1]-width_indexes_out[0])

    def _data_getter(
        signal: np.ndarray | list,
        img_data: np.ndarray,
        info: dict[str, Any],
        accumulator_func: Callable[..., np.ndarray],
        index_iter: int,
        back_fore_indexer: int,
    ) -> None:
        """
        Fill *signal* in-place with (accumulated) frame data for one iteration.

        Iterates over all configuration steps and their frames, crops each
        image to ``new_image_size``, stacks the frames, and reduces them
        with *accumulator_func*.

        Parameters
        ----------
        signal : np.ndarray
            Output array of shape ``(config_num, height, width)``; filled
            in-place.
        img_data : np.ndarray
            Raw image data from the SIF file.
        info : dict
            Experiment metadata dictionary.
        accumulator_func : Callable[..., np.ndarray]
            Function that reduces the per-configuration frame stack along
            axis ``0``.
        index_iter : int
            Current iteration index.
        back_fore_indexer : int
            Selects signal (``0``) or background (``1``) frames.
        """
        for i in range(config_num):
            frames = len(info["indices_full"][index_iter][i][back_fore_indexer])
            acc_signal = np.zeros((frames, *new_image_size))
            acc_signal[:] = img_data[info['indices_full'][index_iter][i][back_fore_indexer]][:, slice(*height_indexes_out), slice(*width_indexes_out)]
            signal[i] = accumulator_func(acc_signal)

    def _over_n_iter(
        function: Callable[[np.ndarray | list, int], None],
        n_iter: int,
        curr_shape: tuple[int, ...],
        axis_names: tuple[str, ...]
    ) -> tuple[np.ndarray | list, tuple[str, ...]]:
        """
        Apply *function* for each iteration index and return the stacked result.

        Parameters
        ----------
        function : Callable[[np.ndarray, int], None]
            Callable that fills an output array for a given iteration index.
        n_iter : int
            Total number of iterations.
        curr_shape : tuple[int, ...]
            Shape of the output array for a single iteration.

        Returns
        -------
        np.ndarray | list
            Array of shape *curr_shape* when ``n_iter == 1``, or
            ``(n_iter, *curr_shape)`` otherwise.
        """
        if n_iter == 1:
            if as_list:
                signal = [np.zeros(curr_shape[1:]) for _ in range(curr_shape[0])]
            else:
                signal = np.zeros(curr_shape)
            function(signal, 0)
        else:
            shape = (n_iter,) + curr_shape
            axis_names = ("iterations",) + axis_names
            if as_list:
                signal = [[np.zeros(curr_shape[1:]) for _ in range(curr_shape[0])] for _ in range(n_iter)]
            else:
                signal = np.zeros(shape)
            for index in range(n_iter):
                function(signal[index], index)

        return signal, axis_names

    def accumulator_data(
        info: dict[str, Any],
        img_data: np.ndarray,
        accumulator_func: Callable[..., np.ndarray | list],
        indexer: int,
        axis_names: tuple[str, ...],
    ) -> tuple[np.ndarray | list, tuple[str, ...]]:
        """
        Build the frame-accumulated data array across all iterations and
        configuration steps.

        Parameters
        ----------
        info : dict
            Experiment metadata dictionary.
        img_data : np.ndarray
            Raw image data from the SIF file.
        accumulator_func : Callable[..., np.ndarray | list]
            Reduction function applied along the frame axis.
        indexer : int
            Selects signal (``0``) or background (``1``) frames.

        Returns
        -------
        np.ndarray | list
            Array of shape ``(config_num, height, width)`` or
            ``(n_iter, config_num, height, width)``.
        """
        axis_names = (axis_names[0],) + axis_names[2:]
        data_shape = (config_num, *new_image_size)
        def _partial_func(signal: np.ndarray | list, index_iter: int) -> None:
            _data_getter(signal, img_data, info, accumulator_func, index_iter, indexer)
        return _over_n_iter(_partial_func, info["n_iter"], data_shape, axis_names)

    def full_data(
        info: dict[str, Any],
        img_data: np.ndarray,
        foreground: bool,
        axis_names: tuple[str, ...],
    ) -> tuple[np.ndarray | list, tuple[str, ...]]:
        """
        Build the non-accumulated data array, retaining all individual frames.

        Parameters
        ----------
        info : dict
            Experiment metadata dictionary.
        img_data : np.ndarray
            Raw image data from the SIF file.
        foreground: bool
            If ``True``, return signal frames; if ``False``, return background frames.

        Returns
        -------
        np.ndarray
            Array of shape ``(config_num, n_frames, height, width)`` or
            ``(n_iter, config_num, n_frames, height, width)``.
        """
        index = 0 if foreground else 1
        n_frames_set = set(info["n_frames"])
        if len(n_frames_set) != 1:
            msg = ("When no accumulator function is used, all configurations must have the same number of frames. "
                   f"Found {list(n_frames_set)}")
            raise ValueError(msg)

        if foreground:
            n_frames = info["n_frames"][0]
        else:
            n_frames = BackgroundConfiguration(info["background_every"]).background_count(info["n_frames"][0])

        data_shape = (config_num, n_frames, *new_image_size)

        def _partial_func(signal: np.ndarray | list, index_iter: int) -> None:
            _data_getter(signal, img_data, info, (lambda x: x), index_iter, index)

        return _over_n_iter(_partial_func, info["n_iter"], data_shape, axis_names)

    def get_the_data(foreground) -> tuple[np.ndarray | list, tuple[str, ...]]:
        index = 0 if foreground else 1

        height_name = "height" if img_info["NumberOfSubImages"] == 1 else "fiber"
        axis_names = ("config", "frames", height_name, "width")

        if config_flattener is None:
            data_out, axis_names = full_data(info, img_data, foreground, axis_names)
        elif isinstance(config_flattener, (Callable, str)):
            accumulator_func = _get_accumulator(config_flattener, axis=-3, name="iter_accumulator")
            data_out, axis_names = accumulator_data(info, img_data, accumulator_func, index, axis_names)
        else:
            msg = f"`iter_accumulator` must be either a str of Callable, not {type(config_flattener).__name__}"
            raise ValueError(msg)

        if height_flattener is not None:
            axis_names = axis_names[:-2] + (axis_names[-1],)
            accumulator_func = _get_accumulator(height_flattener, axis=-2, name="flatten_height")
            data_out = accumulator_func(data_out)

        return data_out, axis_names

    data, axis_names = get_the_data(True)
    background = get_the_data(False)[0] if has_background else None

    if not as_list:
        while any(n == 1 for n in data.shape):
            keep_dims = [i for i, n in enumerate(data.shape) if n != 1]
            new_dims_fore = [data.shape[i] for i in keep_dims]
            axis_names = tuple(name for index, name in enumerate(axis_names) if index in keep_dims)
            data = data.reshape(new_dims_fore)
            if has_background:
                new_dims_back = [background.shape[i] for i in keep_dims]
                background = background.reshape(new_dims_back)

    return Measurement(data, background, wavelengths, axis_names, info, img_info)


def _get_wavelengths(img_info, width_indexes: tuple[float, float] | None=None):
    """Return wavelength calibration values for detector columns.

    Parameters
    ----------
    sif_loc : str | PathLike[str]
        Path to the Andor SIF image file.
    width_indexes : tuple[float, float] | None
        Optional width crop applied before calibration.

    Returns
    -------
    np.ndarray
        Wavelength value for each selected detector column.
    """
    image_size = img_info['size']

    indexes = np.arange(0, image_size[0]) + 1
    cal_data = img_info['Calibration_data']
    wavelengths = np.polynomial.polynomial.polyval(indexes, cal_data)
    width_indexes = _check_width_indexes(width_indexes, image_size[0], wavelengths)

    if width_indexes is not None:
        mask = (width_indexes[0] <= (indexes-1)) & ((indexes-1) < width_indexes[1])
        wavelengths = wavelengths[mask]

    return wavelengths


def get_info(pickle_loc: _file_path_type) -> dict[str, Any]:
    """Load and return the experiment metadata dictionary from a pickle file.

    Parameters
    ----------
    pickle_loc : str | PathLike[str]
        Path to the pickle file containing experiment metadata.

    Returns
    -------
    dict[str, Any]
        Experiment metadata dictionary.
    """
    with open(pickle_loc, "rb") as f:
        info = pickle.load(f)
    return info


def get_data_glued(
        sif_locs: _file_path_or_collection_type,
        pickle_locs: _file_path_or_collection_type,
        *,
        remove_overlap: bool = True,
        include_background: bool | Literal['auto'] = 'auto',
        intensity_factors: Collection[float] | None = None,
        **get_data_kwargs: Unpack[GetDataKwargs]
) -> CombinedMeasurement:
    """
    Glue the wavelengths of multiple measurements together

    Parameters
    ----------
    sif_locs: _file_path_or_collection_type
    pickle_locs: _file_path_or_collection_type
    remove_overlap: bool
    include_background: bool | Literal['auto']
    intensity_factors: Collection[float] | None
    get_data_kwargs: Unpack[GetDataKwargs]

    Returns
    -------
    CombinedMeasurement
    """
    if get_data_kwargs.get('width_indexes') is not None:
        warnings.warn("Gluing with `width_indexes` may result in gaps")
    if get_data_kwargs.get("as_list"):
        raise NotImplementedError("Gluing with `as_list` == True not implemented")

    if isinstance(sif_locs, _file_path_type):
        if not isinstance(pickle_locs, _file_path_type):
            raise ValueError("Found multiple pickle files, but only one sif file.")  # noqa: TRY004
        return CombinedMeasurement.from_measurement(get_data(sif_locs, pickle_locs, **get_data_kwargs))

    sif_locs = cast(Collection[_file_path_type], sif_locs)

    if isinstance(pickle_locs, _file_path_type):
        pickle_locs = [pickle_locs]*len(sif_locs)

    pickle_locs = cast(Collection[_file_path_type], pickle_locs)

    if len(pickle_locs) != len(sif_locs):
        msg = f"The length of `pickle_locs` and `sif_locs` should be the same, found {len(pickle_locs)} and {len(sif_locs)}"
        raise ValueError(msg)

    datas = [get_data(sif_loc, pickle_loc) for (pickle_loc, sif_loc) in zip(pickle_locs, sif_locs, strict=True)]
    infos = tuple(data.info for data in datas)
    img_infos = tuple(data.sif_info for data in datas)
    axis_names = tuple(data.axis_names for data in datas)

    unique_measurements = {info["experiment_type"] for info in infos}
    if len(unique_measurements) != 1:
        unique_measurements = list(unique_measurements)
        measurement_names = ", ".join(unique_measurements[:-1]) + f", and {unique_measurements[-1]}"
        msg = f"Cannot join different types of measurements. Found: {measurement_names}."
        raise ValueError(msg)

    if include_background:
        has_a_background = [data.has_background for data in datas]
        if not all(has_a_background) and any(has_a_background):
            idx = [str(i) for i in range(len(datas)) if datas[i][1]]
            if len(idx) == 1:
                idx_msg = idx
            else:
                idx_msg = ", ".join(idx[:-1]) + f", and {idx[-1]}"
            msg = f"Found background at index(es) {idx_msg}, but not at the others. Set `include_background` to False to exclude all backgrounds."
            raise ValueError(msg)

        if include_background is True and not has_a_background[0]:
            raise ValueError("Did not find any backgrounds, while `include_background` is True. Set to False or 'auto' to continue without background.")

        has_background = has_a_background[0]
    else:
        has_background = False

    expected_shape = datas[0].intensity.shape[:-1]
    for index, data in enumerate(datas[1:], start=1):
        found_shape = data.intensity.shape[:-1]

        if len(found_shape) != len(expected_shape):
            raise ValueError(f"Measurements have different number of dimensions at index 0 ({len(expected_shape)}) "
                             f"and {index} ({len(found_shape)}).")

        if data.intensity.shape[:-1] != expected_shape:
            if index == 1:
                msg = f"Found incompatible shape[:-1] between index 0 and 1, at 0: {expected_shape}, at 1: {data[0].shape[:-1]}."
            else:
                msg = f"Found incompatible shape[:-1] at index: {index}. Found: {data[0].shape[:-1]}, expected {expected_shape}."

            height_flattened = get_data_kwargs.get("height_flattener", None) is not None
            wrong_dimensions = [index for index, (x, y) in enumerate(zip(data.intensity.shape[:-1], expected_shape)) if x != y]
            if not height_flattened and len(wrong_dimensions) == 1 and wrong_dimensions[0] == (len(expected_shape) - 2):
                msg += "It seems that only the heights are incompatible, add a `height_flattener` to the `get_data_kwargs` to fix the error."

            raise ValueError(msg)

    wavelengths = [data.wavelengths for data in datas]
    sorted_indexes = np.argsort([wav[0] for wav in wavelengths])

    if intensity_factors is None:
        intensity_factors = [1 for _ in range(len(sif_locs))]
    elif len(intensity_factors) != len(sif_locs):
        msg = f"The length of `intensity_factors` and `sif_locs` should be the same, found {len(pickle_locs)} and {len(sif_locs)}"
        raise ValueError(msg)

    data_for = [inten_factor*data.intensity for inten_factor, data in zip(intensity_factors, datas)]
    if has_background:
        data_back = [inten_factor*data.background for inten_factor, data in zip(intensity_factors, datas)]
    else:
        data_back = None

    if remove_overlap:
        select_indexes: list[tuple[int, int]] = [(0, len(wav)) for wav in wavelengths]

        for i in range(len(sorted_indexes)-1):
            if not wavelengths[i+1][0] < wavelengths[i][-1]:
                continue
            middle = (wavelengths[i+1][0] + wavelengths[i][-1]) / 2
            select_indexes[i] = (select_indexes[i][0], np.searchsorted(wavelengths[i], middle))
            select_indexes[i+1] = (np.searchsorted(wavelengths[i+1], middle), select_indexes[i+1][1])

        wavelengths = [wav[slice(*idx)] for wav, idx in zip(wavelengths, select_indexes)]
        data_for = [data[..., slice(*idx)] for data, idx in zip(data_for, select_indexes)]
        if has_background:
            data_back = [data[..., slice(*idx)] for data, idx in zip(data_back, select_indexes)]

    wavelengths = np.concatenate(wavelengths)
    data_for = np.concatenate(data_for, axis=-1)
    if has_background:
        data_back = np.concatenate(data_back, axis=-1)

    if not remove_overlap:
        idx = np.argsort(wavelengths)
        data_for = data_for[..., idx]
        if has_background:
            data_back = data_back[..., idx]

    return CombinedMeasurement(data_for, data_back, wavelengths, axis_names[0], infos, img_infos)


def _read_or_pass_get_data(
        sif: Measurement | _file_path_type,
        pickle_loc: _file_path_type | None,
        /,
        **kwargs: Unpack[GetDataKwargs]
) -> Measurement:
    if isinstance(sif, Measurement):
        return sif

    if pickle_loc is None:
        raise ValueError("If `sif` is a path, `pickle_loc` must be given.")

    return get_data(sif, pickle_loc, **kwargs)


def _read_or_pass_get_data_glued(
        sif: CombinedMeasurement | _file_path_or_collection_type,
        pickle_loc: _file_path_or_collection_type | None,
        /,
        **kwargs: Unpack[GetDataGluedKwargs]
) -> CombinedMeasurement:
    if isinstance(sif, CombinedMeasurement):
        return sif

    if pickle_loc is None:
        raise ValueError("If `sif` is a path, `pickle_loc` must be given.")

    return get_data_glued(sif, pickle_loc, **kwargs)