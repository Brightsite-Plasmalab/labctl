from typing_extensions import List, Unpack
from labctl.devices import ThorlabsStageCmds
from labctl.experiments.camera import CameraExperiment, CameraExperimentKwargs


class Raman2DExperimentKwargs(CameraExperimentKwargs):
    filters: list[str]

class Raman2DExperiment(CameraExperiment):
    filterstage: ThorlabsStageCmds

    def __init__(self, filters: list[str], **kwargs: Unpack[CameraExperimentKwargs]):
        self.filters = filters
        super().__init__(**kwargs)
        self.check_N_frames(len(self.filters), " One configuration for each filter.")

    def prepare_config(self, cmds, i):
        cmds.append(f"# Selecting filter {i}")

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
        info = super().make_postprocessing_info()
        info.update({
            "variable": "filters",
            "filters": self.filters,
        })
        return info
