from pathlib import Path

import numpy as np

from labctl.experiments import CameraTimesweepExperiment

# %%
dest_folder = Path(r"D:/bnc_test2")
times = np.linspace(0, 2, 3)*1e-2
print(times)

experiment = CameraTimesweepExperiment(
    camera_delay_optimum=0,
    delta_t = times,
    n_iter=1,
    n_frames=1,
    t_exposure=0.1,
    background_every=0,
    dest_folder=dest_folder,
    camera_channel="C",
    laser_frequency=30,
    file_name="bnc_commands2",
    camera_pulse_width=1e-2,
    camera_reset_time = 0.025,
)

experiment.save_labctl_script(overwrite=True)
experiment.save_postprocessing_info(overwrite=True)
# %%
dest_folder = Path(r"E:\26_08_25\labctl")
#
# times = np.array([0, 10, 20, 40, 80, 160, 320, 640, 1280])*1e-9
# times = np.arange(0, 10, 1)*1e-8
times = np.arange(1, 11, 2)*1e-8
# times = [0, 3e-8, 1e-7, 3e-7, 1e-6]

# pulse_len = 0.5/1020
# times = [0.1*pulse_len, 0.3*pulse_len, 0.5*pulse_len, 0.7*pulse_len, 0.9*pulse_len, 2*pulse_len - 30e-6]
# times = [t + 1/1020 for t in times]
# times = np.linspace(0, 0.55/1020, 21) + 1/1020
print(times)

experiment = CameraTimesweepExperiment(
    camera_delay_optimum=464e-9,
    # camera_delay_optimum=0,
    delta_t = times,
    n_iter=1,
    n_frames=10,
    t_exposure=2.5,
    # background_every=BackgroundConfiguration.BEGIN,
    background_every=0,
    dest_folder=dest_folder,
    camera_channel="C",
    laser_frequency=30,
    file_name="LIF",
    camera_reset_time = 0.05,
)

experiment.save_labctl_script(overwrite=True)
experiment.save_postprocessing_info(overwrite=True)