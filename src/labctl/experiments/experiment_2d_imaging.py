from typing_extensions import List
from labctl.devices import ThorlabsStageCmds
from labctl.experiments.base_camera_experiment import BaseCameraExperiment


class Raman_2D_Experiment(BaseCameraExperiment):
    filters: list[str]
    filterstage: ThorlabsStageCmds

    def __init__(self, filters, **kwargs):
        self.filters = filters
        super().__init__(**kwargs)

    def get_config_names(self) -> List[str]:
        return self.filters

    def prepare_config(self, cmds, i):
        cmds += f"# Selecting filter {i}"

        if i == 0:
            # Filter 0 is selected by homing
            self.filterstage.home()
        else:
            # Other filters are selected by jogging forward
            self.filterstage.forward()

    def make_labctl_header(self):
        cmds = super().make_labctl_header()

        self.filterstage = ThorlabsStageCmds(cmds)
        cmds.register_device(self.filterstage, 1)

        return cmds

    def make_postprocessing_info(self):
        return {"filters": self.filters, **super().make_postprocessing_info()}
