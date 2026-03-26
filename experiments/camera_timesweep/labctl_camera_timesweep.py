from pathlib import Path

import numpy as np

from labctl.experiments import CameraTimesweepExperiment

dest_folder = Path(r"D:\experiment 24 mrt 2026")
times = np.linspace(40, 80, 41)*1e-9
print(times)

experiment = CameraTimesweepExperiment(
    camera_delay_optimum=400e-9,
    delta_t = times,
    short_explanation="",
    author="Thijs",
    n_iter=1,
    n_frames=5,
    t_exposure=0.1,
    background_every=0,
    dest_folder=dest_folder,
    camera_channel="C",
    laser_frequency=30,
    file_name=f"Raman_timing",
)

experiment.save_labctl_script()
experiment.save_postprocessing_info()
# %%
