from abc import abstractmethod
from typing_extensions import List
from labctl.script import Script
from labctl.experiments.base_camera_experiment import BaseCameraExperiment


class TemplateExperiment(BaseCameraExperiment):

    def __init__(
        self,
        **kwargs,
    ):
        super().__init__(**kwargs)

    @abstractmethod
    def get_config_names(self) -> List[str]:
        """Get the human-readable names of the configurations."""
        pass

    def prepare_experiment(self, cmds: Script):
        """Prepare the experiment. Inherit this method to add more commands."""
        pass

    @abstractmethod
    def prepare_config(self, cmds, i):
        """Prepares experimental configuration i."""
        pass

    def get_camera_delay(self, config, version):
        """Get the camera delay for a specific configuration, frame, and version."""
        if version == 0:
            # foreground
            return self.camera_delay_optimum
        else:
            # background
            return self.camera_delay_background

    def shutdown_experiment(self):
        """Shutdown the experiment. Inherit this method to add more commands."""
        pass
