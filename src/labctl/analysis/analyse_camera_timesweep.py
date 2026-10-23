"""Convenience plotting helper for camera-delay timesweep experiments."""
import numpy as np

from labctl._type_hints import _file_path_or_collection_type
from labctl.analysis import CombinedMeasurement
from labctl.analysis.plotter import plot_vs_variable
from labctl.analysis.read_data import GetDataGluedKwargs


def analyse_camera_timesweep_intensity(
        sif: CombinedMeasurement | _file_path_or_collection_type,
        pickle_loc: _file_path_or_collection_type | None = None,
        /, *,
        get_data_glued_kwargs: GetDataGluedKwargs | None = None,
        plot_vs_variable_kwargs: dict | None = None,
        plot_kwargs: dict | None = None
) -> None:
    """
    Plot camera-timesweep intensity versus configured delay.

    Parameters
    ----------
    sif : CombinedMeasurement | _file_path_or_collection_type
        The measurement data, or path to the sif file.
    pickle_loc: _file_path_or_collection_type | None = None
        Path to pickle file, must be given if sif is a _file_path_or_collection_type.
    get_data_glued_kwargs: GetDataGluedKwargs | None
        Used to process the data if sif is a path. Passed to :func:`labctl.analysis.get_data_glued`.
    """
    plot_kwargs = plot_kwargs or {}
    plot_vs_variable_kwargs = plot_vs_variable_kwargs or {}

    default_kwargs = {
        "show": True,
        "x_label": "Camera delay (s)",
    }
    default_kwargs.update(**plot_vs_variable_kwargs)
    default_plot_kwargs = {
        "marker": 'o',
        "color": "k",
        "alpha": 0.5,
        "linestyle": "none"
    }
    default_plot_kwargs.update(**plot_kwargs)

    def print_max(x, y):
        x_unique = np.unique(x)
        avg_values = [np.median(y[unique_val == x]) for unique_val in x_unique]
        idx = avg_values.index(max(avg_values))
        print(f"Max value at {x_unique[idx]:.2e}s")
        return x, y

    plot_vs_variable(
        sif,
        pickle_loc,
        plot_kwargs=default_plot_kwargs,
        get_data_glued_kwargs=get_data_glued_kwargs,
        data_modifier = print_max,
        **default_kwargs
    )

