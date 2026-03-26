# This script is used to process the data from a polarization filter calibration experiment. It assumes the data is stored in a .sif file with 2D images for each angle of the polarization filter.

import pickle

import numpy as np
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit

from labctl.analysis.get_data import get_data


def analyse_polarization_calibration(
        sif_loc,
        pickle_loc,
        *,
        indexes = None,
        deg_fit_lims = None,
        initial_guess = (100, 10_000, 0.6 * np.pi)
):
    # Load pickle file
    info = pickle.load(open(pickle_loc, "rb"))

    if info['experiment_type'] != 'PolarisationFilterCalibrationExperiment':
        msg = f"Function only works for 'PolarisationFilterCalibrationExperiment' not {info['experiment_type']}."
        raise ValueError(msg)

    data = get_data(sif_loc, pickle_loc, width_indexes=indexes)[0]

    def fit_func(x, A, B, C):
        return A + B * np.cos(x * np.pi / 180 - C) ** 2

    data_mean = np.mean(data, axis = (1, 2))
    data_flat = data_mean.flatten()

    degs = np.asarray(info['alpha'])
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

    plt.plot(x, y, 'r-')
    plt.plot(degs, data_flat, 'ko', alpha=0.5)
    plt.plot(ang_max, B_max, 'ro', label=rf'Max: {ang_max:.2f} $\pm {np.sqrt(pcov[2, 2]):.4f} \degree $')
    plt.xlabel("Rotation [deg]")
    plt.ylabel("Intensity")
    plt.legend(loc='upper right')
    plt.show()

    print(f"{popt=}\n{pcov=}")

    data_med = np.mean(data, axis=(3,))
    normalized_intensity = data_med / np.sum(data_med, axis=2)[:, :, None]

    rows = np.arange(data_med.shape[-1])[None, None, :]
    average = np.sum(rows * normalized_intensity, axis=2)

    plt.figure()
    plt.plot(degs, average, 'ko', alpha=0.5)
    plt.ylabel("Laser location [px]")
    plt.xlabel("Rotation [deg]")
    plt.grid()

