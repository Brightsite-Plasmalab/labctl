from labctl.experiments.camera import BackgroundConfiguration, CameraExperiment
from typing_extensions import List, override


class SimpleExperiment(CameraExperiment):
    @override
    def get_config_names(self) -> List[str]:
        # Only one configuration
        return [""]

    @override
    def prepare_config(self, cmds, i):
        # No configuration to prepare
        pass
