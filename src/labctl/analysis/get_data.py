import functools
import pickle
from collections.abc import Callable
from os import PathLike
from typing import Literal

import numpy as np
import sif_parser


def _get_data(
    data: np.ndarray,
    info: dict,
    indexer: int,
    frame_index: int,
    iter_index: int = 0,
) -> np.ndarray:
    """
    Extract a single frame from the raw image data using the index mapping stored in *info*.

    Parameters
    ----------
    data : np.ndarray
        Raw image data loaded from the SIF file, indexed by frame number.
    info : dict
        Experiment metadata dictionary containing the ``'indices'`` mapping.
    indexer : int
        Selects signal (``0``) or background (``1``) frame indices.
    frame_index : int
        Index of the frame within the current configuration step.
    iter_index : int, optional
        Index of the current acquisition iteration (default ``0``).

    Returns
    -------
    np.ndarray
        Squeezed image array for the requested frame.
    """
    indexes = info['indices'][iter_index][frame_index][indexer]
    return np.squeeze(data[indexes, :, :])


def _config_num(info: dict) -> int:
    """
    Return the number of experiment configuration steps stored in *info*.

    Parameters
    ----------
    info : dict
        Experiment metadata dictionary.  Must contain a ``'variable'`` key
        whose value is the name (or a list whose first element is the name)
        of the sweep variable, and a corresponding key whose value is the
        list of swept values.

    Returns
    -------
    int
        Number of configuration steps.

    Raises
    ------
    ValueError
        If the ``'variable'`` key is absent from *info*.
    """
    if "variable" in info:
        variable = info["variable"]
        if not isinstance(variable, str):
            variable = variable[0]
        return len(info[variable])
    else:
        raise ValueError("No 'variable' key found in info, cannot extract experiment variable(s).")
    

_acc_typehint = Literal["median", "mean", "sum"] | Callable[..., np.ndarray]


def _get_accumulator(
    value: _acc_typehint,
    axis: int,
    name: str,
) -> Callable[..., np.ndarray]:
    """
    Return an accumulator callable bound to *axis*.

    Parameters
    ----------
    value : _acc_typehint
        Either a string shorthand for a built-in NumPy reduction
        (``'median'``, ``'mean'``, or ``'sum'``) or a custom callable that
        already performs its own reduction.
    axis : int
        Axis along which the built-in reduction is applied when *value* is
        a string.  Ignored for custom callables.
    name : str
        Name of the parameter being validated; used only in error messages.

    Returns
    -------
    Callable[..., np.ndarray]
        A callable that performs the requested reduction on an array.

    Raises
    ------
    ValueError
        If *value* is an unrecognised string or is neither a string nor a
        callable.
    """
    if isinstance(value, str):
        match value:
            case "median":
                func = np.median
            case "mean":
                func = np.mean
            case "sum":
                func = np.sum
            case _:
                msg = f"Only 'median', 'mean', or 'sum' are valid values str value for `{name}`."
                raise ValueError(msg)
        return functools.partial(func, axis=axis)
    elif isinstance(value, Callable):
        return value
    else:
        msg = f"Expected str or Callable for `{name}`, got {type(value).__name__}."
        raise ValueError(msg)


def _set_indexes(
    given_value: tuple[int, int] | None,
    dir_image_size: int,
    name: str,
) -> tuple[int, int]:
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
    tuple[int, int]
        Validated ``(start, stop)`` pixel range.

    Raises
    ------
    ValueError
        If the range is empty, starts below zero, or exceeds the image
        dimension.
    """
    if given_value is None:
        return 0, dir_image_size
    elif given_value[0] >= given_value[1]:
        msg = f"For `{name}_indexes` first value should be smaller than second value, found {given_value}"
        raise ValueError(msg)
    elif given_value[0] < 0:
        msg = f"For `{name}_indexes` first value should be bigger or equal to zero, found {given_value[0]}"
        raise ValueError(msg)
    elif given_value[1] > dir_image_size:
        msg = (f"For `{name}_indexes` second value should be smaller or equal to image size ({dir_image_size}), "
               f"found {given_value[0]}")
        raise ValueError(msg)
    else:
        return given_value[0], given_value[1]


def get_data(
    sif_loc: str | PathLike[str],
    pickle_loc: str | PathLike[str],
    *,
    width_indexes: tuple[int, int] | None = None,
    height_indexes: tuple[int, int] | None = None,
    iter_accumulator: _acc_typehint | None = None,
) -> tuple[np.ndarray, np.ndarray | None]:
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
    width_indexes : tuple[int, int] | None, optional
        ``(start, stop)`` pixel crop along the width axis.  ``None`` uses
        the full width.
    height_indexes : tuple[int, int] | None, optional
        ``(start, stop)`` pixel crop along the height axis.  ``None`` uses
        the full height.
    iter_accumulator : _acc_typehint | None, optional
        How to collapse repeated acquisition iterations into a single value.

        * ``None`` – keep every frame individually; all configurations must
          have the same number of frames.
        * ``'median'``, ``'mean'``, or ``'sum'`` – apply the named NumPy
          reduction over the frame axis (axis ``-3``).
        * A callable that performs a custom reduction over axis ``-3``.

    Returns
    -------
    tuple[np.ndarray, np.ndarray | None]
        A 2-tuple ``(data, background)``.

        * Without *iter_accumulator* the arrays have shape
          ``(config_num, n_frames, height, width)``.
        * With an *iter_accumulator* the frame dimension is collapsed:
          ``(config_num, height, width)``.
        * When the experiment contains multiple iterations an extra leading
          axis is prepended: ``(n_iter, config_num, ...)``.
        * *background* is ``None`` when no background frames were recorded
          (``background_every == 0``).

    Raises
    ------
    ValueError
        If any index crop is out of range, or if *iter_accumulator* is
        ``None`` and configurations have differing numbers of frames.
    """
    with open(pickle_loc, "rb") as f:
        info = pickle.load(f)
    img_data, img_info = sif_parser.np_open(sif_loc)
    image_size = img_info['size']
    has_background = info["background_every"] != 0

    config_num = _config_num(info)

    width_indexes = _set_indexes(width_indexes, image_size[0], "width_indexes")
    height_indexes = _set_indexes(height_indexes, image_size[1], "height_indexes")
    new_image_size = (height_indexes[1]-height_indexes[0], width_indexes[1]-width_indexes[0])

    def _data_getter(
        signal: np.ndarray,
        img_data: np.ndarray,
        info: dict,
        accumulator_func: Callable[..., np.ndarray],
        index_iter: int,
        indexer: int,
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
        indexer : int
            Selects signal (``0``) or background (``1``) frames.
        """
        nonlocal new_image_size
        index = 0
        for i, frames in enumerate(info["n_frames"]):
            acc_signal = np.zeros((frames, *new_image_size))

            for j in range(frames):
                data = _get_data(img_data, info, index, index_iter, indexer)
                acc_signal[j] = data[:, :, slice(*width_indexes)]
            signal[i] = accumulator_func(acc_signal)

    def _over_n_iter(
        function: Callable[[np.ndarray, int], None],
        n_iter: int,
        curr_shape: tuple[int, ...],
    ) -> np.ndarray:
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
        np.ndarray
            Array of shape *curr_shape* when ``n_iter == 1``, or
            ``(n_iter, *curr_shape)`` otherwise.
        """
        if n_iter == 1:
            signal = np.zeros(curr_shape)
            function(signal, 0)
            return signal
        else:
            shape = (n_iter,) + curr_shape
            signal = np.zeros(shape)
            for index in range(n_iter):
                function(signal[index], index)
            return signal

    def accumulator_data(
        info: dict,
        img_data: np.ndarray,
        accumulator_func: Callable[..., np.ndarray],
        n_iter: int,
        indexer: int,
    ) -> np.ndarray:
        """
        Build the frame-accumulated data array across all iterations and
        configuration steps.

        Parameters
        ----------
        info : dict
            Experiment metadata dictionary.
        img_data : np.ndarray
            Raw image data from the SIF file.
        accumulator_func : Callable[..., np.ndarray]
            Reduction function applied along the frame axis.
        n_iter : int
            Number of repetition iterations.
        indexer : int
            Selects signal (``0``) or background (``1``) frames.

        Returns
        -------
        np.ndarray
            Array of shape ``(config_num, height, width)`` or
            ``(n_iter, config_num, height, width)``.
        """
        nonlocal new_image_size
        data_shape = (config_num, *new_image_size)
        partial_func = functools.partial(_data_getter, img_data=img_data, info=info, accumulator_func=accumulator_func,
                                         indexer=indexer)
        return _over_n_iter(partial_func, n_iter, data_shape)

    def full_data(
        info: dict,
        img_data: np.ndarray,
        n_frames: int,
        n_iter: int,
        indexer: int,
    ) -> np.ndarray:
        """
        Build the non-accumulated data array, retaining all individual frames.

        Parameters
        ----------
        info : dict
            Experiment metadata dictionary.
        img_data : np.ndarray
            Raw image data from the SIF file.
        n_frames : int
            Number of frames per configuration step.  Must be identical
            across all steps when this function is used.
        n_iter : int
            Number of repetition iterations.
        indexer : int
            Selects signal (``0``) or background (``1``) frames.

        Returns
        -------
        np.ndarray
            Array of shape ``(config_num, n_frames, height, width)`` or
            ``(n_iter, config_num, n_frames, height, width)``.
        """
        nonlocal new_image_size
        data_shape = (config_num, n_frames, *new_image_size)
        partial_func = functools.partial(_data_getter, img_data=img_data, info=info, accumulator_func=lambda x: x,
                                         indexer=indexer)
        return _over_n_iter(partial_func, n_iter, data_shape)

    if iter_accumulator is None:
        n_frames_set = set(info["n_frames"])
        if len(n_frames_set) != 1:
            msg = ("When no accumulator function is used, all configurations must have the same number of frames."
                   f"Found {list(n_frames_set)}")
            raise ValueError(msg)
        n_frames = info["n_frames"][0]
        caller = functools.partial(full_data, info, img_data, n_frames)
    elif isinstance(iter_accumulator, Callable | str):
        accumulator_func = _get_accumulator(iter_accumulator, axis=-3, name="iter_accumulator")
        caller = functools.partial(accumulator_data, info, img_data, accumulator_func, info["n_iter"])
    else:
        msg = f"`iter_accumulator` must be either a str of Callable, not {type(iter_accumulator).__name__}"
        raise ValueError(msg)

    data = caller(0)
    if has_background:
        background = caller(1)
        return data, background
    return data, None


def get_data_2D(
        sif_loc: str | PathLike[str],
        pickle_loc: str | PathLike[str],
        width_indexes: tuple[int, int] | None = None,
        height_indexes: tuple[int, int] | None = None,
        iter_accumulator: _acc_typehint | None = None,
        height_accumulator: _acc_typehint = 'sum',
) -> np.ndarray:
    """
    Load experiment data and collapse the height axis into a 1-D spectrum per
    pixel column.

    Convenience wrapper around :func:`get_data` that additionally applies
    *height_accumulator* along the height dimension (axis ``-2``), reducing
    2-D images to 1-D arrays.

    Parameters
    ----------
    sif_loc : str | PathLike[str]
        Path to the Andor SIF image file.
    pickle_loc : str | PathLike[str]
        Path to the pickle file containing experiment metadata.
    width_indexes : tuple[int, int] | None, optional
        ``(start, stop)`` pixel crop along the width axis.  ``None`` uses
        the full width.
    height_indexes : tuple[int, int] | None, optional
        ``(start, stop)`` pixel crop along the height axis.  ``None`` uses
        the full height.
    iter_accumulator : _acc_typehint | None, optional
        Reduction applied over repeated acquisition iterations (see
        :func:`get_data` for full details).
    height_accumulator : _acc_typehint, optional
        Reduction applied along the height axis (axis ``-2``) after loading.
        Defaults to ``'sum'``.

    Returns
    -------
    np.ndarray
        Data array with the height dimension collapsed.  Shape is
        ``((n_iter,) config_num, (n_frames,) width)`` depending on whether
        *iter_accumulator* is provided and on the number of iterations.
    """
    # data shape ((n_iter,) config_num, (n_fames,) height, width
    data = get_data(sif_loc, pickle_loc, width_indexes=width_indexes, height_indexes=height_indexes, 
                    iter_accumulator=iter_accumulator)

    accumulator_func = _get_accumulator(height_accumulator, axis=-2, name="height_accumulator")
    # new shape ((n_iter,) config_num, (n_fames,) width
    return accumulator_func(data)


def get_wavelengths(sif_loc, width_indexes=None):
    _, img_info = sif_parser.np_open(sif_loc, lazy='memmap')
    image_size = img_info['size']

    width_indexes = _set_indexes(width_indexes, image_size[0], 'width_indexes')
    indexes = np.arange(*width_indexes)
    cal_data = img_info['Calibration_data']
    wavelengths = np.full_like(indexes, cal_data[0])
    for index, val in enumerate(cal_data[1:], start=1):
        wavelengths += val*(indexes**index)
    return wavelengths
