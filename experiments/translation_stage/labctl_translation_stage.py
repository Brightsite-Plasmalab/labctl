from pathlib import Path
import random

import numpy as np

from labctl.experiments import TranslationStageExperiment

dest_folder = Path(r"E:\experiment 10 jun 2026")
x = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
random.seed(10)
random.shuffle(x)


for t, n in ((0.25, 10), (0.5, 10), (1, 10), (2, 10), (4, 5), (8, 5), (16, 5)):
    exp = TranslationStageExperiment(
        x = x,
        camera_delay_optimum=469e-9,
        background_every=0,
        n_iter=1,
        n_frames=n,
        t_exposure=t,
        camera_reset_time=0.2,
        dest_folder=dest_folder,
        camera_channel="C",
        laser_frequency=30,
        file_name=f"S4_Thomson_{t}s_{n}",
    )

    exp.save_labctl_script()
    exp.save_postprocessing_info()
