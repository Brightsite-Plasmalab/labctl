from typing_extensions import List
from labctl.devices import ThorlabsRotationStageCmds
from labctl.script import Script
from labctl.experiments.base_camera_experiment import BaseCameraExperiment


class PolarisationFilterExperiment(BaseCameraExperiment):
    alpha_ver: float
    alpha_hor: float
    rotationstage: ThorlabsRotationStageCmds

    def __init__(self, alpha_ver, alpha_hor, **kwargs):
        self.alpha_ver = alpha_ver
        self.alpha_hor = alpha_hor
        super().__init__(**kwargs)

    def get_config_names(self) -> List[str]:
        return ["ver", "hor"]

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
            cmds += f"# Selecting vertical rotation: {alphai:.3f} degrees"
            self.rotationstage.goto_degrees(alphai)
        else:
            alphai = self.alpha_hor
            cmds += f"# Selecting horizontal rotation: {alphai:.3f} degrees"
            self.rotationstage.goto_degrees(alphai)

    def make_postprocessing_info(self):
        return {
            "alpha_ver": self.alpha_ver,
            "alpha_hor": self.alpha_hor,
            **super().make_postprocessing_info(),
        }
