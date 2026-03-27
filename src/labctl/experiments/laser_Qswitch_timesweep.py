from typing_extensions import Unpack
from labctl.experiments.camera import CameraExperiment, CameraExperimentKwargs


# TODO: Implement laser Qswitch timesweep capabilities

class LaserTimesweepExperimentKwargs(CameraExperimentKwargs):
    t0: float
    delta_t: list[float]


class LaserTimesweepExperiment(CameraExperiment):
    def __init__(self, t0: float, delta_t: list[float], **kwargs: Unpack[CameraExperimentKwargs]):
        raise NotImplementedError("LaserTimesweepExperiment is not yet implemented.")
        self.t0 = t0
        self.delta_t = delta_t
        super().__init__(**kwargs)
        if type(self) is LaserTimesweepExperiment:
            self.check_N_frames(len(self.delta_t))

    def prepare_config(self, cmds, i):
        cmds.append(f"# Setting laser Q-switch delay to {self.t0 + self.delta_t[i]:.3e} s")
        # TODO: Here you would add commands to set the laser Q-switch delay

    def make_postprocessing_info(self):
        info = super().make_postprocessing_info()
        info.update({
            "variable": "t",
            "delta_t": self.delta_t,
            "t0": self.t0,
            "t": [ti + self.t0 for ti in self.delta_t],
        })
        return info
