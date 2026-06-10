from pathlib import Path

from labctl.experiments import PolarisationFilterExperiment, BackgroundConfiguration

dest_folder = Path(r"C:\Users\P70095200\Downloads")

experiment = PolarisationFilterExperiment(
    alpha_ver = 22.84,
    short_explanation = "",
    author = "Thijs",
    n_iter = 1,
    n_frames = [10, 5],
    t_exposure = 50,
    camera_delay_optimum=462e-9,
    background_every=BackgroundConfiguration.BEGIN,
    dest_folder = dest_folder,
    camera_channel = "C",
    laser_frequency = 30,
    file_name = f"S3",
)

experiment.save_labctl_script()
experiment.save_postprocessing_info()
# %%