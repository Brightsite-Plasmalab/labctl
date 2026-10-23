import warnings

import matplotlib.pyplot as plt
import numpy as np
import sif_parser
from numpy.polynomial import Polynomial
from scipy.signal import find_peaks
from scipy.stats import pearsonr

from labctl._type_hints import _file_path_type


def multitrack_calibration(sif_loc: _file_path_type, out_loc: _file_path_type | None):
    img_data, _img_info = sif_parser.np_open(sif_loc)

    data_m = np.sum(img_data, axis=(0, -1))
    data_m = (data_m - data_m.min()) / (data_m.max() - data_m.min())

    peaks = find_peaks(data_m, height=0.5, prominence=0.05)[0]

    min_vals = []
    for i in range(len(peaks)-1):
        num = peaks[i] + np.argmin(data_m[peaks[i]:peaks[i+1]])
        min_vals.append(num)

    start = peaks[0] - 2*(peaks[1] - peaks[0])
    end = peaks[-1] + 2*(peaks[-1] - peaks[-2])

    def axvlines(ax, data, color, label):
        ax.axvline(data[0], color=color, label=label)
        for dat in data[1:]:
            ax.axvline(dat, color=color)

    fig, ax = plt.subplots()
    ax.plot(data_m/data_m.max(), color='k', label="Intensity")
    axvlines(ax, peaks, "r", "peaks")
    axvlines(ax, min_vals, "b", "valleys")
    ax.set_xlim(start, end)
    ax.set_ylabel("Relative intensity")
    ax.set_xlabel("Vertical pixel")
    ax.legend()
    fig.show()

    fit = Polynomial.fit(np.arange(len(min_vals))+1, min_vals, 1)

    indexes = fit(np.arange(20)).astype(int)

    x_vals = np.concatenate([
        np.arange(len(peaks)),
        np.arange(len(min_vals))+0.5,
    ])
    y_vals = np.concatenate((peaks, min_vals))
    print(f"Peak Pearson r^2: {pearsonr(x_vals, y_vals)[0]**2:.6f}")
    print(indexes)

    fig, ax = plt.subplots()
    ax.plot(x_vals, y_vals, "o")
    ax.set_ylabel("Vertical pixel")
    ax.set_xlabel("Peak/valley number")
    fig.show()

    if out_loc is not None:
        lines = ["[Custom]\n", f"{len(indexes)-1}\n"]

        for i in range(len(indexes)-1):
            lines.append(f"{indexes[i]+1} {indexes[i+1]} {1}\n")

        with open(out_loc, "w") as file:
            file.writelines(lines)
    else:
        warnings.warn("No output generated since `out_loc` is None")