from pathlib import Path

from labctl.experiments import SimpleCameraExperiment

dest_folder = Path(r"D:\bnc_test")

experiment = SimpleCameraExperiment(
    camera_delay_optimum=484e-9,
    n_iter=1,
    n_frames=1,
    t_exposure=0.1,
    background_every=0,
    dest_folder=dest_folder,
    camera_channel="C",
    laser_frequency=30,
    file_name="484ns",
)

experiment.save_postprocessing_info()
experiment.save_labctl_script()
