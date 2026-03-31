"""Raman 2D filter-sweep experiment definitions."""

from typing_extensions import Unpack
from labctl.devices import ThorlabsStageCmds
from labctl.experiments.camera import CameraExperiment, CameraExperimentKwargs


class Raman2DExperimentKwargs(CameraExperimentKwargs):
    """Keyword arguments for :class:`Raman2DExperiment`."""

    filters: list[str]


class Raman2DExperiment(CameraExperiment):
    """Acquire camera data while stepping through a filter wheel sequence."""

    filterstage: ThorlabsStageCmds
    filters: list[str]

    def __init__(self, filters: list[str], **kwargs: Unpack[CameraExperimentKwargs]) -> None:
        """Initialize a Raman filter sweep.

        Parameters
        ----------
        filters : list[str]
            Ordered filter names used as experiment configurations.
        **kwargs : Unpack[CameraExperimentKwargs]
            Base camera experiment configuration.
        """
        self.filters = filters
        super().__init__(**kwargs)
        if type(self) is Raman2DExperiment:
            self.check_N_frames(len(self.filters), " One configuration for each filter.")

    def prepare_config(self, cmds, i: int) -> None:
        """Select the filter for configuration ``i``.

        Parameters
        ----------
        cmds : Script
            Script command collector.
        i : int
            Configuration index.
        """
        cmds.comment(f"Selecting filter {i}")

        if i == 0:
            # Filter 0 is selected by homing
            self.filterstage.home()
        else:
            # Other filters are selected by jogging forward
            self.filterstage.forward()

    def get_config_names(self) -> list[str]:
        """Return configured filter names.

        Returns
        -------
        list[str]
            Filter labels in acquisition order.
        """
        return self.filters

    def make_labctl_header(self):
        """Create script header and register the filter stage.

        Returns
        -------
        Script
            Initialized script object with registered devices.
        """
        cmds = super().make_labctl_header()

        self.filterstage = ThorlabsStageCmds(cmds)
        cmds.register_device(self.filterstage, 1)

        return cmds

    def make_postprocessing_info(self) -> dict[str, object]:
        """Build postprocessing metadata for filter sweeps.

        Returns
        -------
        dict[str, object]
            Metadata dictionary containing filter labels.
        """
        info = super().make_postprocessing_info()
        info.update(
            {
                "variable": "filters",
                "filters": self.filters,
            }
        )
        return info


    def make_postprocessing_script(self) -> str | None:
        """Return a postprocessing script template when implemented.

        Returns
        -------
        str | None
            Script source string when implemented; currently ``None``.
        """
        pass  # TODO
