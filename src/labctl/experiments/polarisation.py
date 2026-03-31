"""Two-state polarization experiment definitions.

This module defines a convenience experiment for vertical/horizontal
polarization measurements using two fixed rotation angles.
"""

from typing import cast

from typing_extensions import NotRequired, Unpack
from labctl.devices import ThorlabsRotationStageCmds
from labctl.experiments import PolarisationFilterSweepExperiment
from labctl.experiments.polarisation_sweep import PolarisationFilterSweepExperimentKwargs
from labctl.experiments.camera import CameraExperimentKwargs


class PolarisationFilterExperimentKwargs(CameraExperimentKwargs):
    """Keyword arguments for :class:`PolarisationFilterExperiment`."""

    alpha_ver: float
    alpha_hor: NotRequired[float]


class PolarisationFilterExperiment(PolarisationFilterSweepExperiment):
    """Acquire data for vertical and horizontal polarization states."""

    rotationstage: ThorlabsRotationStageCmds
    alpha_ver: float
    alpha_hor: float

    def __init__(
        self,
        alpha_ver: float,
        alpha_hor: float | None = None,
        **kwargs: Unpack[CameraExperimentKwargs],
    ) -> None:
        """Initialize a two-angle polarization experiment.

        Parameters
        ----------
        alpha_ver : float
            Vertical polarization angle.
        alpha_hor : float | None, optional
            Horizontal polarization angle. Defaults to ``alpha_ver + 90``.
        **kwargs : Unpack[CameraExperimentKwargs]
            Base camera experiment settings.

        Raises
        ------
        ValueError
            If ``alpha_ver`` is not provided.
        """
        if alpha_ver is None:
            msg = "alpha_ver must be provided as a (keyword) argument"
            raise ValueError(msg)
        self.alpha_ver = alpha_ver
        if alpha_hor is None:
            alpha_hor = alpha_ver + 90.0
        self.alpha_hor = alpha_hor

        kwargs = cast(PolarisationFilterSweepExperimentKwargs, kwargs)
        kwargs['alpha'] = [alpha_ver, alpha_hor]

        super().__init__(**kwargs)
        if type(self) is PolarisationFilterExperiment:
            self.check_N_frames(2, " One configuration for each polarization.")

    def get_config_names(self) -> list[str]:
        """Return the fixed configuration names.

        Returns
        -------
        list[str]
            ``["ver", "hor"]``.
        """
        return ["ver", "hor"]

    def prepare_config(self, cmds, i: int) -> None:
        """Select vertical or horizontal configuration.

        Parameters
        ----------
        cmds : Script
            Script command collector.
        i : int
            Configuration index.
        """
        names = ["vertical", "horizontal"]
        cmds.append(f"# Selecting {names[i]} rotation")
        super().prepare_config(cmds, i)

    def make_postprocessing_info(self) -> dict[str, object]:
        """Build postprocessing metadata for fixed polarization states.

        Returns
        -------
        dict[str, object]
            Metadata dictionary with vertical/horizontal angle values.
        """
        info = super().make_postprocessing_info()
        info.update(
            {
                "alpha_ver": self.alpha_ver,
                "alpha_hor": self.alpha_hor,
            }
        )
        return info
