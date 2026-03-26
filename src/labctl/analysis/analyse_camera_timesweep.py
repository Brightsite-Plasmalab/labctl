import pickle

import numpy as np
import matplotlib.pyplot as plt

from labctl.analysis.get_data import get_data

def analyse_camera_timesweep(
        sif_loc,
        pickle_loc,
        *,
        indexes = None,
):
    # Load pickle file
    info = pickle.load(open(pickle_loc, "rb"))

    if info['experiment_type'] != 'CameraTimesweepExperiment':
        msg = f"Function only works for 'CameraTimesweepExperiment' not {info['experiment_type']}."
        raise ValueError(msg)

    data = get_data(sif_loc, pickle_loc, width_indexes=indexes)[0]
    data_mean = np.mean(data, axis = (1, 2))
    data_flat = data_mean.flatten()
    time_values = info["t"]
    repeated_time_values = np.repeat(time_values, info["n_frames"][0])

    data_total = np.median(data_mean, axis=1)
    max_time = np.argmax(data_total)
    print(f"Maximum signal at {max_time*1e9:.1f} ns")

    fig, ax = plt.subplots()
    ax.plot(1e9*repeated_time_values, data_flat, 'ko', alpha=0.5)
    ax.grid(True)
    ax.set_xlabel('Camera delay [ns]')
    ax.set_ylabel('Amplitude [A.U]')
    fig.show()