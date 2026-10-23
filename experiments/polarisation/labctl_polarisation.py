from pathlib import Path

from labctl.experiments import BackgroundConfiguration, PolarisationFilterExperiment

dest_folder = Path(r"E:\26_08_20\labctl")
# %%
# (0.05, 20), (0.1, 20), (0.25, 20), (0.5, 20), (1, 20), (2, 15), (4, 12), (8, 10), (16, 6)
for t, n in ((0.05, 40), (0.1, 40), (0.25, 40), (0.5, 40), (1, 40), (2, 30), (4, 24), (8, 20), (16, 12)):
    if n > 10:
        back = BackgroundConfiguration.BEGIN_END
    else:
        back = BackgroundConfiguration.BEGIN

    experiment = PolarisationFilterExperiment(
        alpha_ver = 28.63,
        n_iter = 1,
        n_frames = [n, n],
        t_exposure = t,
        camera_delay_optimum=464e-9,
        background_every=back,
        dest_folder = dest_folder,
        camera_channel = "C",
        laser_frequency = 30,
        file_name = f"polarisation_{t}_{n}",
    )

    experiment.save_labctl_script()
    experiment.save_postprocessing_info()
# %%
experiment = PolarisationFilterExperiment(
    alpha_ver = 28.63,
    n_iter = 1,
    n_frames = [15, 6],
    t_exposure = 16,
    camera_delay_optimum=464e-9,
    background_every=BackgroundConfiguration.BEGIN_END,
    dest_folder = dest_folder,
    camera_channel = "C",
    laser_frequency = 30,
    file_name = "polarisation_16s_15",
)

experiment.save_labctl_script()
experiment.save_postprocessing_info()
