"""Template experiment base for custom camera-based experiments."""

from abc import abstractmethod
from labctl.script import Script
from labctl.experiments.camera import CameraExperiment


class TemplateExperiment(CameraExperiment):
    """Minimal scaffold for new camera experiment implementations."""

    def __init__(
        self,
        **kwargs,
    ) -> None:
        """Initialize template experiment.

        Parameters
        ----------
        **kwargs
            Keyword arguments accepted by :class:`CameraExperiment`.
        """
        super().__init__(**kwargs)
        if type(self) is TemplateExperiment:
            self.check_N_frames(len(self.configs), " One configuration for each element in configs.")

    def prepare_experiment(self, cmds: Script) -> None:
        """Prepare the experiment. Inherit this method to add more commands."""
        pass

    @abstractmethod
    def prepare_config(self, cmds: Script, i: int) -> None:
        """Prepare experimental configuration ``i``.

        Parameters
        ----------
        cmds : Script
            Script command collector.
        i : int
            Configuration index.
        """
        pass

    # TODO change to new get_camera_delay_background and get_camera_delay_foreground
    def get_camera_delay_foreground(self, config: int) -> float:
        """Return foreground camera delay for a configuration.

        Parameters
        ----------
        config : int
            Configuration index.

        Returns
        -------
        float
            Camera delay in seconds.
        """
        pass

    def get_camera_delay_background(self, config: int) -> float:
        """Return background camera delay for a configuration.

        Parameters
        ----------
        config : int
            Configuration index.

        Returns
        -------
        float
            Camera delay in seconds.
        """
        pass

    def shutdown_experiment(self) -> None:
        """Shutdown the experiment. Inherit this method to add more commands."""
        pass
