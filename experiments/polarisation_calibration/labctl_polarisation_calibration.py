# Polarisation filter calibration
# Used when the spectrometer optics stack contains a rotation stage for a polarisation filter.
# This script will make an angle sweep to determine the position corresponding to vertical polarisation.*
# %%
from pathlib import Path

import numpy as np

from labctl.experiments import (
        BackgroundConfiguration,
        PolarisationFilterSweepExperiment,
)

dest_folder = Path(r"D:\26_08_17\cali")

angle_start = 0
angle_end = 360
exposure = 0.1

degrees = np.linspace(angle_start, angle_end, 31, endpoint=False)
experiment = PolarisationFilterSweepExperiment(
        alpha = degrees,
        n_iter = 1,
        n_frames = [5 for _ in degrees],
        t_exposure = exposure,
        camera_delay_optimum=409e-9,
        background_every=BackgroundConfiguration.BEGIN,
        dest_folder = dest_folder,
        camera_channel = "C",
        laser_frequency = 30,
        file_name = "angle_calibration",
        camera_reset_time=0.5,
    )

experiment.save_labctl_script(overwrite=True)
experiment.save_postprocessing_info(overwrite=True)
# %%
