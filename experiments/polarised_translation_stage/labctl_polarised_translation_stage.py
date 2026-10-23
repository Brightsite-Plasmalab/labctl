from pathlib import Path

from experiments import BackgroundConfiguration, PolarisedTranslationStageExperiment

dest_folder = Path(r"D:\26_07_10\raman")
# dest_folder = Path(r"C:\Users\P70095200\Downloads")
x = [0, 4, 8]  # , 6, 8, 10, 12
pol = 156.57 + 180
# random.seed(10)
# random.shuffle(x)

# ((0.05, 20), (0.1, 20), (0.25, 20), (0.5, 20), (1, 20), (2, 15), (4, 12), (8, 10), (16, 10))
for t, n in ((16, 5),):
    exp = PolarisedTranslationStageExperiment(
        x = x,
        alpha_ver=pol,
        camera_delay_optimum=469e-9,
        background_every=BackgroundConfiguration.BEGIN,
        n_iter=1,
        n_frames=n,
        t_exposure=t,
        camera_reset_time=0.2,
        dest_folder=dest_folder,
        camera_channel="C",
        laser_frequency=30,
        file_name=f"Raman_{t}s_{n}_048",
    )

    exp.save_labctl_script()
    exp.save_postprocessing_info()

# %%