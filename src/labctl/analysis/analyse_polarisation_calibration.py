"""Analysis helper for polarisation filter calibration experiments."""

import warnings

import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import curve_fit

from labctl._type_hints import _file_path_type
from labctl.analysis import Measurement
from labctl.analysis.read_data import GetDataKwargs, _read_or_pass_get_data


def analyse_polarisation_calibration(
        sif: Measurement | _file_path_type,
        pickle_loc: _file_path_type | None = None,
        /, *,
        get_data_kwargs: GetDataKwargs | None = None,
        deg_fit_lims= None,
        initial_guess=(200, 10, 0.6 * np.pi),
        combine_frames = False,
) -> None:
    """Fit and visualize polarisation calibration response.

    Parameters
    ----------
    sif : Measurement | _file_path_type
        The measurement data, or path to the sif file.
    pickle_loc: _file_path_type | None
        Path to pickle file, must be given if sif is a _file_path_type.
    get_data_kwargs: GetDataKwargs | None
        Used to process the data if sif is a path. Passed to `get_data`
    deg_fit_lims : tuple[float, float] | None, optional
        Degree limits used for curve fitting.
    initial_guess : tuple[float, float, float], optional
        Initial guess for cosine-squared fit parameters.
    combine_frames: bool
        Whether to take a median over the `frames` axis.
    """
    data = _read_or_pass_get_data(sif, pickle_loc, **(get_data_kwargs or {}))

    for name in ("height", "frames"):
        if name not in data.axis_names:
            warnings.warn(f"`{name}` axis not in measurement data, but best results gotten when they are present")

    info = data.info

    average_axis = tuple([index for index, name in enumerate(data.axis_names) if name in ("width", "height")])
    average_axis = average_axis if len(average_axis) > 0 else None

    def apply_average(value):
        if average_axis is None:
            return value
        else:
            return np.mean(value, axis=average_axis)

    if data.has_background:
        back_mean = apply_average(data.background)
    else:
        back_mean = np.full((data.intensity.shape[0:2]), np.median(data.intensity))

    def fit_func(x, A, B, C):
        return A + B * np.cos(x * np.pi / 180 - C) ** 2

    data_mean = apply_average(data.intensity)
    if combine_frames:
        data_flat = np.median(data_mean, axis=1)
    else:
        data_flat = data_mean.flatten()

    data_mean -= back_mean

    if 'variable' in info:
        degs = info[info['variable']]
    else:
        degs = info['alpha']
    degs = np.asarray(degs)

    if not combine_frames:
        degs = np.repeat(degs, info["n_frames"][0])

    if deg_fit_lims is None:
        deg_fit_lims = -np.inf, np.inf
    idx_fit = (degs > deg_fit_lims[0]) & (degs < deg_fit_lims[1])
    popt, pcov = curve_fit(fit_func, degs[idx_fit], data_flat[idx_fit], p0=initial_guess,
                           bounds=([0, 0, 0], [np.inf, np.inf, np.pi]))

    x = np.linspace(degs.min(),  degs.max(), 100)
    y = fit_func(x, *popt)

    B_max = popt[1] + popt[0]
    C_max = popt[2]

    ang_max = C_max * 180 / np.pi

    print("Highest signal ", ang_max)

    fig, ax = plt.subplots(layout = 'constrained')
    ax.plot(degs, data_flat, 'ko', alpha=0.5, label="Measured")
    ax.plot(x, y, 'r-', label="Best fit")
    ax.plot(ang_max, B_max, 'ro', label=rf'Max: ${ang_max:.2f}\degree \pm {np.sqrt(pcov[2, 2]):.4f} \degree $')
    ax.set_xlabel("Rotation [deg]")
    ax.set_ylabel("Intensity")
    ax.legend(loc='upper right')
    fig.show()

    vals = fit_func(degs, *popt)

    fig, ax = plt.subplots(layout = "constrained")
    ax.plot(degs, data_flat / vals, "ko", alpha=0.5)
    ax.set_xlabel("Rotation [deg]")
    ax.set_ylabel("Ratio measured / fit intensity")
    fig.show()


    print(f"{popt=}\n{pcov=}")

    if 'height' in data.axis_names:
        if combine_frames:
            data = data.apply_over_axis("median", "frames")
        data = data.apply_over_axis("mean", "width")

        data_med, back_med = data.intensity, data.background
        if not data.has_background:
            back_med = np.full(data_med.shape, np.median(data.intensity))

        data_corr = data_med - back_med
        if combine_frames:
            normalized_intensity = data_corr / np.sum(data_corr, axis=-1)[:, None]
            rows = np.arange(data_med.shape[-1])[None, :]
        else:
            normalized_intensity = data_corr / np.sum(data_corr, axis=-1)[:, :, None]
            rows = np.arange(data_med.shape[-1])[None, None, :]

        average = np.sum(rows * normalized_intensity, axis=-1)

        locs = [(ang_max + x) % 360 for x in (0, 90, 180, 270)]

        fig, ax = plt.subplots(layout="constrained")
        ax.plot(degs, average.flatten(), 'ko', alpha=0.5, label="Measurement")
        ax.set_ylabel("Laser location (px)")
        ax.set_xlabel("Rotation (deg)")
        ax.axvline(locs[0], label="Pol. angles")
        for loc in locs[1:]:
            ax.axvline(loc)
        ax.legend()
        ax.grid()
        fig.show()

