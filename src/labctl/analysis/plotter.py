import warnings
from collections.abc import Callable, Iterable
from typing import Literal, NotRequired, TypedDict

import matplotlib as mpl
import matplotlib.ticker
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from labctl._type_hints import _file_path_or_collection_type
from labctl.analysis import CombinedMeasurement
from labctl.analysis.read_data import (
    GetDataGluedKwargs,
    _acc_typehint,
    _get_accumulator,
    _read_or_pass_get_data_glued,
)


def _set_labels(info, variable_key, labels, var_name):
    """Resolve x-axis variable name and labels from metadata.

    Parameters
    ----------
    info : dict
        Measurement metadata containing variable definitions.
    variable_key : str | None
        Metadata key holding the variable values.
    labels : Iterable[str] | None
        Explicit labels to use.
    var_name : str | None
        Display name for the variable.

    Returns
    -------
    tuple[str, Iterable]
        The resolved variable name and associated labels.

    Raises
    ------
    ValueError
        If metadata contains multiple variables while a single variable is
        required.
    """
    has_labels = labels is not None
    has_var_name = var_name is not None

    if has_var_name and has_labels:
        return var_name, labels

    if variable_key is None:
        variable_key = info['variable']
        if not isinstance(variable_key, str):
            msg = f"The experiment should have 1 variable, not {len(variable_key)}: {variable_key}"
            raise ValueError(msg)

    if not has_var_name:
        var_name = variable_key
    if not has_labels:
        labels = info[variable_key]

    return var_name, labels


class PlotVsWavelengthKwargs(TypedDict):
    variable_key: NotRequired[str]
    var_name: NotRequired[str]
    labels: NotRequired[Iterable[str]]

    plot_type: NotRequired[Literal["normal", "raman"]]
    show: NotRequired[bool]

    colormap: NotRequired[str]
    use_colorbar: NotRequired[bool | Literal['auto']]
    x_label: NotRequired[str | Literal['auto'] | None]
    y_label: NotRequired[str]
    fig_ax: NotRequired[tuple[Figure, Axes]]
    subplots_kwargs: NotRequired[dict]

    use_background: NotRequired[bool | Literal['auto']]
    get_data_glued_kwargs: NotRequired[GetDataGluedKwargs]
    data_modifier: NotRequired[Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray]]

    config_mask: NotRequired[np.ndarray | Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray]]


def plot_vs_wavelength(
        sif: CombinedMeasurement | _file_path_or_collection_type,
        pickle_loc: _file_path_or_collection_type | None = None,
        *,
        var_name: str | None = None,
        labels: Iterable[str] | None = None,
        variable_key: str | None = None,

        show: bool = False,
        plot_type: Literal["normal", "raman"] = "normal",
        use_colorbar: bool | Literal['auto'] = 'auto',
        colormap: str = 'turbo',
        x_label: str | Literal['auto'] | None = 'auto',
        y_label: str = 'Counts (A.U.)',
        fig_ax: tuple[Figure, Axes] | None = None,
        subplots_kwargs: dict | None = None,

        use_background: bool | Literal['auto'] = 'auto',
        get_data_glued_kwargs: GetDataGluedKwargs | None = None,
        data_modifier: Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray] | None = None,

        config_mask: np.ndarray | Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray] | None = None
) -> tuple[Figure, Axes] | None:
    """Plot spectra against wavelength or Raman shift.

    Parameters
    ----------
    sif : CombinedMeasurement | _file_path_or_collection_type
        Input measurement object or path(s) used to load data.
    pickle_loc : _file_path_or_collection_type | None, optional
        Pickle sidecar path(s) corresponding to *sif* input.
    var_name : str | None, optional
        Legend title for configuration labels.
    labels : Iterable[str] | None, optional
        Explicit per-configuration labels.
    variable_key : str | None, optional
        Metadata key used to derive labels.
    show : bool, optional
        If ``True``, display the figure and return ``None``.
    plot_type : {"normal", "raman"}, optional
        Plot x-axis as wavelength or Raman shift.
    use_colorbar : bool | Literal['auto'], optional
        Whether to encode traces by colorbar; ``'auto'`` enables colorbar for
        larger config stacks.
    colormap : str, optional
        Matplotlib colormap name used with colorbar mode.
    x_label : str | Literal['auto'] | None, optional
        X-axis label override. ``'auto'`` keeps mode-specific defaults.
    y_label : str, optional
        Y-axis label.
    fig_ax : tuple[Figure, Axes] | None, optional
        Existing figure/axes pair to draw on.
    subplots_kwargs : dict | None, optional
        Keyword arguments passed to :func:`matplotlib.pyplot.subplots` when a
        new figure is created.
    use_background : bool | Literal['auto'], optional
        Background subtraction mode forwarded to
        :meth:`CombinedMeasurement.get_corrected_intensity`.
    get_data_glued_kwargs : GetDataGluedKwargs | None, optional
        Data-loading options for :func:`get_data_glued<labctl.analysis.get_data_glued>`.
    data_modifier : Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray] | None, optional
        Post-load transformation applied to ``(x, y, labels)``.
    config_mask : np.ndarray | Callable[[np.ndarray, np.ndarray, np.ndarray], np.ndarray] | None, optional
        Boolean mask (or mask factory) selecting plotted configurations.

    Returns
    -------
    tuple[Figure, Axes] | None
        Figure and axes when ``show`` is ``False``; otherwise ``None``.

    Raises
    ------
    ValueError
        If wavelength axis is not available in the input data.
    """
    get_data_glued_kwargs = get_data_glued_kwargs or {}
    get_data_glued_kwargs.setdefault("config_flattener", "mean")
    get_data_glued_kwargs.setdefault("height_flattener", "sum")

    data = _read_or_pass_get_data_glued(sif, pickle_loc, **get_data_glued_kwargs)

    if 'frames' in data.axis_names:
        data = data.apply_over_axis("median", axis="frames")
    if 'height' in data.axis_names:
        data = data.apply_over_axis("sum", axis="height")

    if not data.has_wavelengths:
        raise ValueError("Cannot plot vs wavelength when wavelength is not included")

    y = data.get_corrected_intensity(use_background=use_background)
    x = data.wavelengths

    var_name, labels = _set_labels(data.infos[0], variable_key, labels, var_name)
    labels = np.array(labels)

    if config_mask is not None:
        if isinstance(config_mask, Callable):
            config_mask = config_mask(x, y, labels)

        y = y[config_mask]
        labels = labels[config_mask]

    if data_modifier is not None:
        x, y, labels = data_modifier(x, y, labels)

    if fig_ax is None:
        kwargs = {"layout": "constrained"}
        kwargs.update(subplots_kwargs or {})
        fig, ax = plt.subplots(**kwargs)
    else:
        fig, ax = fig_ax

    x = _plot_raman_or_normal(x, plot_type, (fig, ax))

    def get_use_colorbar_bool():
        if isinstance(use_colorbar, bool):
            return use_colorbar
        return bool(y.ndim == 2 and y.shape[0] > 5)

    if get_use_colorbar_bool():
        fig, ax = plot_cbar((fig, ax), x, y, labels, colormap=colormap, var_name=var_name)
    else:
        fig, ax = plot_simple((fig, ax), x, y, labels, var_name=var_name)

    sci_fmt = mpl.ticker.ScalarFormatter(useMathText=True)
    sci_fmt.set_scientific(True)
    sci_fmt.set_powerlimits((-3, 3))
    ax.yaxis.set_major_formatter(sci_fmt)

    ax.set_ylabel(y_label)
    ax.grid(which="minor")

    if x_label != 'auto':
        ax.set_xlabel(x_label)

    if show:
        fig.show()
        return None
    else:
        return fig, ax


def plot_vs_variable(
    sif: CombinedMeasurement | _file_path_or_collection_type,
    pickle_loc: _file_path_or_collection_type | None = None,
    *,
    variable_key: str | None = None,
    width_flattener: _acc_typehint = "mean",

    show: bool = False,
    x_label: str | None = None,
    y_label: str = 'Counts (A.U.)',
    fig_ax: tuple[Figure, Axes] | None = None,
    subplots_kwargs: dict | None = None,

    use_background: bool | Literal['auto'] = 'auto',
    get_data_glued_kwargs: GetDataGluedKwargs | None = None,
    data_modifier: Callable[[np.ndarray, np.ndarray], np.ndarray] | None = None,

    config_mask: np.ndarray | Callable[[np.ndarray, np.ndarray], np.ndarray] | None = None,
    plot_kwargs: dict | None = None,
):
    """Plot integrated intensity as a function of experimental variable.

    Parameters
    ----------
    sif : CombinedMeasurement | _file_path_or_collection_type
        Input measurement object or path(s) used to load data.
    pickle_loc : _file_path_or_collection_type | None, optional
        Pickle sidecar path(s) corresponding to *sif* input.
    variable_key : str | None, optional
        Metadata key used for x-values.
    width_flattener : _acc_typehint, optional
        Reduction applied across the width axis.
    show : bool, optional
        If ``True``, display the figure and return ``None``.
    x_label : str | None, optional
        X-axis label override.
    y_label : str, optional
        Y-axis label.
    fig_ax : tuple[Figure, Axes] | None, optional
        Existing figure/axes pair to draw on.
    subplots_kwargs : dict | None, optional
        Keyword arguments passed when creating a new figure.
    use_background : bool | Literal['auto'], optional
        Background subtraction mode.
    get_data_glued_kwargs : GetDataGluedKwargs | None, optional
        Data-loading options for :func:`get_data_glued<labctl.analysis.get_data_glued>`.
    data_modifier : Callable[[np.ndarray, np.ndarray], np.ndarray] | None, optional
        Optional transform applied to ``(x, y)`` before plotting.
    config_mask : np.ndarray | Callable[[np.ndarray, np.ndarray], np.ndarray] | None, optional
        Boolean mask (or mask factory) selecting plotted points.
    plot_kwargs : dict | None, optional
        Extra keyword arguments passed to ``Axes.plot``.

    Returns
    -------
    tuple[Figure, Axes] | None
        Figure and axes when ``show`` is ``False``; otherwise ``None``.
    """
    plot_kwargs = plot_kwargs or {}
    get_data_glued_kwargs = get_data_glued_kwargs or {}
    get_data_glued_kwargs.setdefault("height_flattener", "sum")

    data = _read_or_pass_get_data_glued(sif, pickle_loc, **get_data_glued_kwargs)
    y = data.get_corrected_intensity(use_background=use_background)
    accumulator = _get_accumulator(width_flattener, -1, 'width_flattener')
    y = accumulator(y)

    x_label, x = _set_labels(data.infos[0], variable_key, None, x_label)
    if get_data_glued_kwargs.get("config_flattener") is None:
        x = [val for val, num in zip(x, data.infos[0]["n_frames"], strict=True) for _ in range(num)]
        y = y.flatten()
    x = np.array(x)

    if config_mask is not None:
        if isinstance(config_mask, Callable):
            config_mask = config_mask(x, y)
        y = y[config_mask]

    if data_modifier is not None:
        x, y = data_modifier(x, y)

    subplots_kwargs = subplots_kwargs or {}
    fig_ax = _get_fig_ax(fig_ax, **subplots_kwargs)

    fig, ax = _plot(fig_ax, x, y, **plot_kwargs)

    sci_fmt = mpl.ticker.ScalarFormatter(useMathText=True)
    sci_fmt.set_scientific(True)
    sci_fmt.set_powerlimits((-3, 3))
    ax.yaxis.set_major_formatter(sci_fmt)

    ax.set_ylabel(y_label)
    ax.set_xlabel(x_label)
    ax.grid(True)

    if show:
        fig.show()
        return None
    else:
        return fig, ax

def _get_fig_ax(fig_ax, subplots_kwargs = None):
    """Return an existing ``(fig, ax)`` pair or create a new one.

    Parameters
    ----------
    fig_ax : tuple[Figure, Axes] | None
        Existing figure/axes pair.
    subplots_kwargs : dict | None, optional
        Keyword arguments forwarded to :func:`matplotlib.pyplot.subplots`.

    Returns
    -------
    tuple[Figure, Axes]
        Figure/axes pair ready for plotting.
    """
    if fig_ax is None:
        subplots_kwargs = subplots_kwargs or {}
        return plt.subplots(layout = "constrained", **subplots_kwargs)
    else:
        return fig_ax

def plot_simple(fig_ax, x, y, labels=None, *, var_name=None):
    """Plot one or multiple traces with optional legend labels.

    Parameters
    ----------
    fig_ax : tuple[Figure, Axes] | None
        Existing figure/axes pair or ``None`` to create one.
    x : np.ndarray | Sequence[np.ndarray]
        X values.
    y : np.ndarray | Sequence[np.ndarray]
        Y values.
    labels : Sequence[str] | None, optional
        Per-trace labels.
    var_name : str | None, optional
        Legend title.

    Returns
    -------
    tuple[Figure, Axes]
        Figure and axes containing the plotted data.
    """
    fig, ax = _plot(fig_ax, x, y, labels=labels)
    if labels is not None:
        ax.legend(title=var_name)
    return fig, ax


def plot_cbar(fig_ax, x, y, labels, *, colormap='turbo', var_name=None):
    """Plot traces colored by label values and attach a bounded colorbar.

    Parameters
    ----------
    fig_ax : tuple[Figure, Axes] | None
        Existing figure/axes pair or ``None`` to create one.
    x : np.ndarray | Sequence[np.ndarray]
        X values.
    y : np.ndarray | Sequence[np.ndarray]
        Y values.
    labels : np.ndarray | Sequence
        Values used for color mapping.
    colormap : str, optional
        Matplotlib colormap name.
    var_name : str | None, optional
        Colorbar label.

    Returns
    -------
    tuple[Figure, Axes]
        Figure and axes containing the plotted data.
    """
    fig, ax = _get_fig_ax(fig_ax)
    if var_name is None:
        var_name = ""

    _cbar, colors = bounded_cbar(ax, var_name, labels, colormap)
    _plot((fig, ax), x, y, colors=colors)

    return fig, ax

def _plot(fig_ax, x, y, *, colors=None, labels=None, **plot_kwargs):
    """Plot scalar or stacked traces on an axes object.

    Parameters
    ----------
    fig_ax : tuple[Figure, Axes] | None
        Existing figure/axes pair or ``None`` to create one.
    x : np.ndarray | Sequence[np.ndarray]
        X coordinate array(s).
    y : np.ndarray | Sequence[np.ndarray]
        Y coordinate array(s).
    colors : Sequence | None, optional
        Per-trace colors.
    labels : Sequence[str | None] | None, optional
        Per-trace labels.
    **plot_kwargs
        Extra keyword arguments forwarded to ``Axes.plot``.

    Returns
    -------
    tuple[Figure, Axes]
        Figure and axes used for plotting.
    """
    fig, ax = _get_fig_ax(fig_ax)
    num = len(y) if isinstance(y[0], Iterable) else 1
    if colors is None:
        colors = [f"C{i}" for i in range(num)]
    if labels is None:
        labels = [None for _ in range(num)]

    if isinstance(y[0], Iterable):
        if not isinstance(x[0], Iterable):
            x = [x for _ in range(len(y))]
        for i in range(len(y)):
            kwargs = {'color': colors[i], 'label': labels[i]}
            kwargs.update(**plot_kwargs)
            ax.plot(x[i], y[i], **kwargs)
    else:
        kwargs = {'color': colors[0], 'label': labels[0]}
        kwargs.update(**plot_kwargs)
        ax.plot(x, y, **kwargs)
    return fig, ax

def _plot_raman_or_normal(x, plot_type: Literal["normal", "raman"], fig_ax) -> np.ndarray:
    """Configure x-axis for normal or Raman representation.

    Parameters
    ----------
    x : np.ndarray
        Wavelength axis in nanometers.
    plot_type : {"normal", "raman"}
        Select standard wavelength axis or Raman-shift conversion.
    fig_ax : tuple[Figure, Axes]
        Figure/axes pair to configure.

    Returns
    -------
    np.ndarray
        X-axis values used for plotting.
    """
    _fig, ax = fig_ax

    if plot_type == "normal":
        ax.set_xlabel("Wavelength (nm)")
        return x

    laser_wavelength_nm = 532.05
    forwards = lambda x: 10_000_000 / (10_000_000 / laser_wavelength_nm - x)
    backwards = lambda x: 10_000_000 / laser_wavelength_nm - 10_000_000 / x
    x = backwards(x)

    ax2 = ax.secondary_xaxis("top", functions=(forwards, backwards))

    ax.set_xlabel("Wavenumber (cm$^{-1}$)")
    ax2.set_xlabel("Wavelength (nm)")

    # (mostly) prevent overlap between axis offset and 2nd x-axis tick labels
    offset = ax.yaxis.get_offset_text()
    offset.set_x(-0.075)

    return x


def bounded_cbar(ax, label, values, cmap='turbo', **cbar_kwargs):
    """Create a colorbar with boundaries centered around unique values.

    Parameters
    ----------
    ax : Axes
        Target axes used to host the colorbar.
    label : str
        Colorbar label.
    values: np.ndarray | Sequence
        Values to map to colors.
    cmap: str | plt.Colormap
        Colormap used for mapping.
    **cbar_kwargs
        Extra keyword arguments passed to :func:`matplotlib.pyplot.colorbar`.

    Returns
    -------
    tuple[plt.Colorbar, np.ndarray]
        Created colorbar and RGBA colors mapped from ``values``.
    """
    if isinstance(cmap, str):
        cmap = plt.get_cmap(cmap)

    unique_values = np.sort(np.unique(values))
    boundaries = ([1.5 * unique_values[0] - 0.5 * unique_values[1]] + [(unique_values[i] + unique_values[i + 1]) / 2 for i in range(len(unique_values) - 1)]
                  + [1.5 * unique_values[-1] - 0.5 * unique_values[-2]])
    diff_val = np.diff(unique_values)
    if not np.allclose(diff_val, np.mean(diff_val)):
        warnings.warn(f"The values are not equally spaced: {diff_val}")
    norm = mpl.colors.BoundaryNorm(boundaries, cmap.N)
    colors = cmap(norm(values))
    t_cbar_kwargs = {"ax": ax, "label": label, 'mappable': plt.cm.ScalarMappable(norm=norm, cmap=cmap)}

    tick_loc = [(boundaries[i] + boundaries[i + 1]) / 2 for i in range(len(boundaries) - 1)]
    minor_tick_loc = []
    if len(unique_values) > 10:
        step = int(np.ceil(len(unique_values) / 10))
        shown_idx = np.arange(0, len(unique_values), step)

        minor_tick_loc = [loc for i, loc in enumerate(tick_loc) if i not in shown_idx]
        tick_loc = [tick_loc[i] for i in shown_idx]

    sci_fmt = mpl.ticker.ScalarFormatter(useMathText=True)
    sci_fmt.set_scientific(True)
    sci_fmt.set_powerlimits((-3, 3))

    t_cbar_kwargs.update({'ticks': tick_loc, 'format': sci_fmt})
    t_cbar_kwargs.update(cbar_kwargs)

    cbar = plt.colorbar(**t_cbar_kwargs)
    cbar.ax.yaxis.set_ticks(minor_tick_loc, minor=True)

    return cbar, colors