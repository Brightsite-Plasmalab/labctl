from typing_extensions import override, Unpack

import numpy as np

from labctl.experiments.camera import CameraExperiment, CameraExperimentKwargs

class CameraTimesweepExperimentKwargs(CameraExperimentKwargs):
    delta_t: list[float] | np.ndarray

class CameraTimesweepExperiment(CameraExperiment):
    def __init__(self, delta_t: list[float] | np.ndarray, **kwargs: Unpack[CameraExperimentKwargs]):
        self.delta_t = delta_t
        super().__init__(
            **kwargs
        )
        expl = f" The number of configurations is the number of camera delays."
        self.check_N_frames(len(self.delta_t), expl)

    def make_postprocessing_info(self):
        info = super().make_postprocessing_info()
        info.update({
            "variable": "t",
            "delta_t": self.delta_t,
            "t0": self.camera_delay_optimum,
            "t": [ti + self.camera_delay_optimum for ti in self.delta_t],
        })
        return info

    def prepare_config(self, cmds, i):
        pass

    @override
    def get_camera_delay_foreground(self, config: int) -> float:
        return self.camera_delay_optimum + self.delta_t[config]

    @override
    def get_camera_delay_background(self, config: int) -> float:
        return self.camera_delay_background
