from typing import List
from labctl.devices import ThorlabsRotationStageCmds
from labctl.script import Script
from labctl.experiments.base_camera_experiment import BaseCameraExperiment


class PolarisationFilterCalibrationExperiment(BaseCameraExperiment):
    alpha: list[float]
    rotationstage: ThorlabsRotationStageCmds

    def __init__(self, alpha, **kwargs):
        self.alpha = alpha
        super().__init__(**kwargs)

    def get_config_names(self) -> List[str]:
        return [f"alpha_{alphai:.3f}deg".replace(".", "_") for alphai in self.alpha]

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
        alphai = self.alpha[i]
        cmds += f"# Selecting rotation {i}: {alphai:.3f} degrees"
        self.rotationstage.goto_degrees(alphai)
        # self.rotationstage.move_relative(degrees=20)

    def make_postprocessing_info(self):
        return {"x": self.alpha, **super().make_postprocessing_info()}
