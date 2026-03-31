"""Translation-stage experiment definitions.

This module implements camera experiments that iterate over one or more
translation-stage positions.
"""

from typing_extensions import Unpack

from labctl.devices import PiTranslationStage
from labctl.script import Script
from labctl.experiments.camera import CameraExperiment, CameraExperimentKwargs


class TranslationStageExperimentKwargs(CameraExperimentKwargs):
    """Keyword arguments for :class:`TranslationStageExperiment`."""

    x: list[float]


class TranslationStageExperiment(CameraExperiment):
    """Acquire camera data for a sweep of translation-stage positions."""

    translationstage: PiTranslationStage

    def __init__(
        self,
        x: list[float] | None = None,
        **kwargs: Unpack[CameraExperimentKwargs],
    ) -> None:
        """Initialize a translation-stage sweep experiment.

        Parameters
        ----------
        x : list[float] | None, optional
            Translation positions in millimeters. Must be provided.
        **kwargs : Unpack[CameraExperimentKwargs]
            Base camera experiment configuration.

        Raises
        ------
        ValueError
            If ``x`` is not provided.
        """
        if x is None:
            msg = "x must be provided as a keyword argument"
            raise ValueError(msg)
        self.x = x
        super().__init__(**kwargs)
        if type(self) == TranslationStageExperiment:
            self.check_N_frames(len(self.x), " One configuration for each translation position.")

    def make_labctl_header(self) -> Script:
        """Create script header and register the translation stage.

        Returns
        -------
        Script
            Initialized script object with devices registered.
        """
        cmds = super().make_labctl_header()

        self.translationstage = PiTranslationStage(cmds)
        cmds.register_device(self.translationstage, 2)

        return cmds

    def prepare_experiment(self, cmds: Script) -> None:
        """Prepare translation-stage hardware before acquisition.

        Parameters
        ----------
        cmds : Script
            Script command collector.
        """
        super().prepare_experiment(cmds)

        self.translationstage.stop()
        self.translationstage.SAI()
        self.translationstage.reset_error()
        self.translationstage.set_reference_mode(1, mode="manual")
        self.translationstage.set_servo(1, enable=True)
        self.translationstage.set_position(1, position=0.0)

    def get_config_names(self) -> list[str]:
        """Return configuration names for all stage positions.

        Returns
        -------
        list[str]
            Position labels formatted for script metadata.
        """
        return [f"x_{xi:.3f}mm".replace(".", "_") for xi in self.x]

    def prepare_config(self, cmds: Script, i: int) -> None:
        """Move the stage to the position for configuration ``i``.

        Parameters
        ----------
        cmds : Script
            Script command collector.
        i : int
            Configuration index.
        """
        super().prepare_config(cmds, i)
        xi = self.x[i]
        cmds.comment(f"Selecting position {i}: {xi:.3f} mm")
        self.translationstage.move_to(axis=1, position=xi)

    def shutdown_experiment(self) -> None:
        """Return stage to origin and stop motion after acquisition."""
        super().shutdown_experiment()

        self.translationstage.move_to(axis=1, position=0.0)
        self.translationstage.stop()

    def make_postprocessing_info(self) -> dict[str, object]:
        """Build postprocessing metadata for translation sweeps.

        Returns
        -------
        dict[str, object]
            Metadata dictionary with variable name and translation coordinates.
        """
        info = super().make_postprocessing_info()
        info.update(
            {
                "variable": "translation_loc",
                "translation_loc": self.x,
            }
        )
        return info
