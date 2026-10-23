"""Camera delay sweep experiment definitions.

This module implements a camera-based experiment that sweeps foreground camera
delay offsets and stores timing metadata for postprocessing.
"""

import numpy as np
from typing_extensions import Unpack, override

from labctl.experiments.camera import BaseCameraExperiment, BaseCameraExperimentKwargs


class CameraTimesweepExperimentKwargs(BaseCameraExperimentKwargs):
    """Keyword arguments for :class:`CameraTimesweepExperiment`."""
    delta_t: list[float] | np.ndarray


class CameraTimesweepExperiment(BaseCameraExperiment):
    """Acquire camera frames over a sweep of trigger delays."""

    def __init__(
        self,
        delta_t: list[float] | np.ndarray,
        **kwargs: Unpack[BaseCameraExperimentKwargs],
    ) -> None:
        """Initialize the experiment with delay offsets.

        Parameters
        ----------
        delta_t : list[float] | np.ndarray
            Delay offsets relative to ``camera_delay_optimum``.
        **kwargs : Unpack[BaseCameraExperimentKwargs]
            Base camera experiment configuration.
        """
        self.delta_t = delta_t
        super().__init__(**kwargs)
        expl = " The number of configurations is the number of camera delays."
        if type(self) is CameraTimesweepExperiment:
            self.check_N_frames(len(self.delta_t), expl)

    def make_postprocessing_info(self) -> dict[str, object]:
        """Build postprocessing metadata for the delay sweep.

        Returns
        -------
        dict[str, object]
            Metadata dictionary containing sweep variable information and
            inherited camera metadata.
        """
        info = super().make_postprocessing_info()
        info.update(
            {
                "variable": "delta_t",
                "delta_t": self.delta_t,
                "t0": self.camera_delay_optimum,
                "t": [ti + self.camera_delay_optimum for ti in self.delta_t],
            }
        )
        return info

    def get_config_names(self) -> list[str]:
        """Return human-readable names for each delay configuration.

        Returns
        -------
        list[str]
            Config labels derived from absolute delay values.
        """
        return [
            f"t_{(ti + self.camera_delay_optimum):.3e}_s".replace(".", "_")
            for ti in self.delta_t
        ]

    def prepare_config(self, cmds, i: int) -> None:
        """No-op configuration hook.

        Parameters
        ----------
        cmds : Script
            Script command collector.
        i : int
            Configuration index.
        """

    @override
    def get_camera_delay_foreground(self, config: int) -> float:
        return self.camera_delay_optimum + self.delta_t[config]

    @override
    def get_camera_delay_background(self, config: int) -> float:
        return self.camera_delay_background
