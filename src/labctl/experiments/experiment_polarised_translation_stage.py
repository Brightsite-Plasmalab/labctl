"""Combined translation-stage and polarization experiment definitions."""

from typing import Unpack

from labctl.experiments.polarisation import PolarisationFilterExperimentKwargs
from labctl.experiments.translation_stage import TranslationStageExperimentKwargs
from labctl.script import Script
from labctl.experiments.polarisation import PolarisationFilterExperiment
from labctl.experiments.translation_stage import TranslationStageExperiment


class PolarisedTranslationStageExperimentKwargs(TranslationStageExperimentKwargs, PolarisationFilterExperimentKwargs):
    """Keyword arguments for :class:`PolarisedTranslationStageExperiment`."""

    pass

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

        # Make sure there are n_x * N_pol (2) configurations.
        # If there are just n_x configurations, repeat each N_pol (2) times.

        if len(kwargs["n_frames"]) == n_x:
            kwargs["n_frames"] = [n for n in kwargs["n_frames"] for _ in range(2)]

        super().__init__(**kwargs)

        if type(self) is PolarisedTranslationStageExperiment:
            self.check_N_frames(2*len(self.x), " Two configurations for each translation position (one for each polarization).")

    def get_config_names(self) -> list[str]:
        """Return combined config names in translation-major order.

        Returns
        -------
        list[str]
            Names formatted as ``<translation>_<polarization>``.
        """
        config_names_translation = TranslationStageExperiment.get_config_names(self)
        config_names_polarisation = PolarisationFilterExperiment.get_config_names(self)
        return [
            f"{cn_t}_{cn_p}"
            for cn_t in config_names_translation
            for cn_p in config_names_polarisation
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

    def prepare_experiment(self, cmds: Script):
        """Prepare both translation and polarization hardware.

        Parameters
        ----------
        cmds : Script
            Script command collector.
        """
        super(TranslationStageExperiment, self).prepare_experiment(cmds)
        super(PolarisationFilterExperiment, self).prepare_experiment(cmds)

    def prepare_config(self, cmds: Script, i: int) -> None:
        """Apply translation and polarization settings for config ``i``.

        Parameters
        ----------
        cmds : Script
            Script command collector.
        i : int
            Flattened configuration index.
        """
        super(TranslationStageExperiment, self).prepare_config(cmds, i // 2)
        super(PolarisationFilterExperiment, self).prepare_config(cmds, i % 2)

    def shutdown_experiment(self) -> None:
        """Shutdown both translation and polarization hardware."""
        super(TranslationStageExperiment, self).shutdown_experiment()
        super(PolarisationFilterExperiment, self).shutdown_experiment()

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
                "variable": ["translation_loc", "alpha"],
                "translation_loc": translation_loc,
                "alpha": alpha,
            }
        )
        return info
