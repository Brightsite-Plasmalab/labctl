from abc import abstractmethod
from typing_extensions import List
from labctl.script import Script
from labctl.experiments.camera import CameraExperiment


class TemplateExperiment(CameraExperiment):

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if type(self) is TemplateExperiment:
            self.check_N_frames(len(self.configs), " One configuration for each element in configs.")

    def prepare_experiment(self, cmds: Script):
        """Prepare the experiment. Inherit this method to add more commands."""
        pass

    @abstractmethod
    def prepare_config(self, cmds, i):
        """Prepares experimental configuration i."""
        pass

    # TODO change to new get_camera_delay_background and get_camera_delay_foreground
    def get_camera_delay(self, config, version):
        """Get the camera delay for a specific configuration, frame, and version."""
        if version in (0, "foreground"):
            # foreground
            return self.camera_delay_optimum
        elif version in (1, "background"):
            # background
            return self.camera_delay_background

    def shutdown_experiment(self):
        """Shutdown the experiment. Inherit this method to add more commands."""
        pass
