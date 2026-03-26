from typing_extensions import List, TypedDict, NotRequired, Unpack
from labctl.devices import ThorlabsRotationStageCmds
from labctl.script import Script
from labctl.experiments.camera import CameraExperiment, CameraExperimentKwargs


class PolarisationFilterExperimentKwargs(CameraExperimentKwargs):
    alpha_ver: float
    alpha_hor: NotRequired[float]


class PolarisationFilterExperiment(CameraExperiment):
    rotationstage: ThorlabsRotationStageCmds

    def __init__(self, alpha_ver: float, alpha_hor: float = None, **kwargs: Unpack[CameraExperimentKwargs]):
        self.alpha_ver = alpha_ver
        if alpha_hor is None:
            alpha_hor = alpha_ver + 90.0
        self.alpha_hor = alpha_hor
        super().__init__(**kwargs)
        self.check_N_frames(2, " One configuration for each polarization.")

    def make_labctl_header(self):
        cmds = super().make_labctl_header()

        self.rotationstage = ThorlabsRotationStageCmds(cmds)
        cmds.register_device(self.rotationstage, 1)

        return cmds

    def prepare_experiment(self, cmds: Script):
        super().prepare_experiment(cmds)

        self.rotationstage.home()

    def prepare_config(self, cmds, i):
        super().prepare_config(cmds, i)

        if i == 0:
            alphai = self.alpha_ver
            cmds.append(f"# Selecting vertical rotation: {alphai:.3f} degrees")
            self.rotationstage.goto_degrees(alphai)
        else:
            alphai = self.alpha_hor
            cmds.append(f"# Selecting horizontal rotation: {alphai:.3f} degrees")
            self.rotationstage.goto_degrees(alphai)

    def make_postprocessing_info(self):
        info = super().make_postprocessing_info()
        info.update({
            "variable": "alpha",
            "alpha_ver": self.alpha_ver,
            "alpha_hor": self.alpha_hor,
            "alpha": [self.alpha_ver, self.alpha_hor],
        })
        return info
