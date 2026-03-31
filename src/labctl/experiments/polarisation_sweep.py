"""Polarisation sweep experiment definitions.

This module provides a camera-based experiment that sweeps a rotation stage
over a list of polarization angles.
"""

from typing import Collection

from typing_extensions import Unpack

import numpy as np

from labctl.devices import ThorlabsRotationStageCmds
from labctl.script import Script
from labctl.experiments.camera import CameraExperiment, CameraExperimentKwargs


class PolarisationFilterSweepExperimentKwargs(CameraExperimentKwargs):
    """Keyword arguments for :class:`PolarisationFilterSweepExperiment`."""

    alpha: Collection[float] | np.ndarray[tuple[int], np.dtype[np.floating | np.integer]]


class PolarisationFilterSweepExperiment(CameraExperiment):
    """Camera experiment that acquires data at multiple polarization angles."""

    rotationstage: ThorlabsRotationStageCmds
    alpha: np.ndarray[tuple[int], np.dtype[np.floating | np.integer]]

    def __init__(
            self,
            alpha: Collection[float] | np.ndarray[tuple[int], np.dtype[np.floating | np.integer]],
            **kwargs: Unpack[CameraExperimentKwargs]
    ) -> None:
        """Initialize a polarization-angle sweep.

        Parameters
        ----------
        alpha : Collection[float] | np.ndarray
            Polarization angles in degrees.
        **kwargs : Unpack[CameraExperimentKwargs]
            Base camera experiment settings.
        """
        self.alpha = np.array(alpha)
        super().__init__(**kwargs)
        if type(self) is PolarisationFilterSweepExperiment:
            self.check_N_frames(len(self.alpha), " One configuration for each polarization.")

    def make_labctl_header(self) -> Script:
        """Create script header and register the rotation stage device.

        Returns
        -------
        Script
            Initialized script object with registered devices.
        """
        cmds = super().make_labctl_header()

        self.rotationstage = ThorlabsRotationStageCmds(cmds)
        cmds.register_device(self.rotationstage, 1)
        return cmds

    def prepare_experiment(self, cmds: Script):
        """Prepare hardware before acquisition starts.

        Parameters
        ----------
        cmds : Script
            Script command collector.
        """
        super().prepare_experiment(cmds)

        self.rotationstage.home()

    def get_config_names(self) -> list[str]:
        """Return names for all polarization configurations.

        Returns
        -------
        list[str]
            Configuration labels based on the angle values.
        """
        return [f"alpha_{alphai:.3f}_deg".replace(".", "_") for alphai in self.alpha]

    def prepare_config(self, cmds: Script, i: int) -> None:
        """Select a polarization angle for configuration ``i``.

        Parameters
        ----------
        cmds : Script
            Script command collector.
        i : int
            Configuration index.
        """
        super().prepare_config(cmds, i)
        alphai = self.alpha[i]
        cmds.comment(f"Selecting rotation {i}: {alphai:.3f} degrees")
        self.rotationstage.goto_degrees(alphai)

    def make_postprocessing_info(self) -> dict[str, object]:
        """Build postprocessing metadata for polarization sweeps.

        Returns
        -------
        dict[str, object]
            Metadata dictionary including the sweep variable and angle values.
        """
        info = super().make_postprocessing_info()
        info.update(
            {
                "variable": "polarization_angle",
                "polarization_angle": self.alpha,
            }
        )
        return info
