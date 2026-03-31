from labctl.experiments.camera import BackgroundConfiguration, CameraExperiment
from typing_extensions import override


class SimpleCameraExperiment(CameraExperiment):
    @override
    def get_config_names(self) -> list[str]:
        # Only one configuration
        return [""]

    @override
    def prepare_config(self, cmds, i):
        # No configuration to prepare
        pass

    @override
    def make_postprocessing_info(self):
        return {
            **super().make_postprocessing_info(),
            "variable": None,
        }
