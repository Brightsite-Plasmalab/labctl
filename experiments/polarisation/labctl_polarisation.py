from pathlib import Path

from labctl.experiments import PolarisationFilterExperiment

dest_folder = Path(r"E:\experiment 26 mrt 2026")

experiment = PolarisationFilterExperiment(
    alpha_ver = 22.84,
    short_explanation = "",
    author = "Thijs",
    n_iter = 1,
    n_frames = 10,
    t_exposure = 100,
    camera_delay_optimum=462e-9,
    background_every=0,
    dest_folder = dest_folder,
    camera_channel = "C",
    laser_frequency = 30,
    file_name = f"S1",
)

experiment.save_labctl_script()
experiment.save_postprocessing_info()
# %%