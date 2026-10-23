"""Combined translation-stage and polarization experiment definitions."""

from typing import Unpack

from labctl.experiments.polarisation import (
    PolarisationFilterExperiment,
    PolarisationFilterExperimentKwargs,
)
from labctl.experiments.translation_stage import (
    TranslationStageExperiment,
    TranslationStageExperimentKwargs,
)
from labctl.script import Script


class PolarisedTranslationStageExperimentKwargs(TranslationStageExperimentKwargs, PolarisationFilterExperimentKwargs):
    """Keyword arguments for :class:`PolarisedTranslationStageExperiment`."""


class PolarisedTranslationStageExperiment(
    PolarisationFilterExperiment, TranslationStageExperiment
):
    """Acquire data for each translation position and both polarizations."""

    def __init__(self, **kwargs: Unpack[PolarisedTranslationStageExperimentKwargs]):
        """Initialize the combined experiment.

        Parameters
        ----------
        **kwargs : Unpack[PolarisedTranslationStageExperimentKwargs]
            Combined translation and polarization experiment configuration.
        """
        n_x = len(kwargs["x"])
        kwargs["x"] = [x for x in kwargs["x"] for _ in range(2)]

        # Make sure there are n_x * N_pol (2) configurations.
        # If there are just n_x configurations, repeat each N_pol (2) times.

        n_frames = kwargs["n_frames"]
        if isinstance(n_frames, int):
            n_frames = [n_frames for _ in range(n_x)]
        if len(n_frames) == n_x:
            n_frames = [n for n in n_frames for _ in range(2)]
        kwargs["n_frames"] = n_frames

        super().__init__(**kwargs)
        self.alpha = [a for _ in range(n_x) for a in self.alpha]

        if type(self) is PolarisedTranslationStageExperiment:
            self.check_N_frames(len(self.x), " Two configurations for each translation position (one for each polarization).")
        if len(self.x) != len(self.alpha):
            msg = f"Internal errror: different number of angles ({len(self.alpha)}) and positions ({len(self.x)})"
            raise ValueError(msg)

    def get_config_names(self) -> list[str]:
        """Return combined config names in translation-major order.

        Returns
        -------
        list[str]
            Names formatted as ``<translation>_<polarization>``.
        """
        config_names_translation = TranslationStageExperiment.get_config_names(self)
        config_names_polarisation = PolarisationFilterExperiment.get_config_names(self) * (len(config_names_translation) // 2)

        return [
            f"{cn_t}_{cn_p}"
            for cn_t, cn_p in zip(config_names_translation, config_names_polarisation, strict=True)
        ]

    def make_labctl_header(self) -> Script:
        """Create script header using inherited setup.

        Returns
        -------
        Script
            Initialized script object.
        """
        return super().make_labctl_header()
        # super(PolarisationFilterExperiment, self).make_labctl_header()

    def make_postprocessing_info(self) -> dict[str, object]:
        """Build postprocessing metadata for the combined sweep.

        Returns
        -------
        dict[str, object]
            Metadata dictionary including multi-variable sweep coordinates.
        """
        info = super().make_postprocessing_info()
        # Expand per-translation/per-polarization metadata to match flattened config order.
        translation_loc = [x for x in self.x for _ in range(2)]
        alpha = list(self.alpha) * len(self.x)
        info.update(
            {
                "variable": ("translation_loc", "alpha"),
                "translation_loc": translation_loc,
                "alpha": alpha,
            }
        )
        return info
