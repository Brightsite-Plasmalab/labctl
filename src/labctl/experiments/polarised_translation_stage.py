from typing_extensions import List
from labctl.experiments.polarisation import PolarisationFilterExperiment
from labctl.experiments.translation_stage import TranslationStageExperiment


class PolarisedTranslationStageExperiment(
    PolarisationFilterExperiment, TranslationStageExperiment
):
    """
    This experiment combines the capabilities of the PolarisationFilterExperiment and the TranslationStageExperiment.
    It will run through all combinations of the translation stage positions and polarisation filter angles.
    """

    def get_config_names(self) -> List[str]:
        config_names_translation = TranslationStageExperiment.get_config_names(self)
        config_names_polarisation = PolarisationFilterExperiment.get_config_names(self)
        return [
            f"{cn_t}_{cn_p}"
            for cn_t in config_names_translation
            for cn_p in config_names_polarisation
        ]

    def check_N_frames(self, expected_length, config_explanation):
        N_x = len(self.x)
        N_pol = 2

        # Make sure there are N_x * N_pol configurations.
        # If there are just N_x configurations, repeat each N_pol times.

        if len(self.n_frames) == N_x:
            self.n_frames = [n for n in self.n_frames for _ in range(N_pol)]
        assert (
            len(self.n_frames) == N_x * N_pol
        ), "N_frames should have length N_x * N_pol"

    def prepare_config(self, cmds, i):
        super(TranslationStageExperiment, self).prepare_config(cmds, i)
        super(PolarisationFilterExperiment, self).prepare_config(cmds, i % 2)

    def shutdown_experiment(self):
        super(TranslationStageExperiment, self).shutdown_experiment()
        super(PolarisationFilterExperiment, self).shutdown_experiment()

    def make_postprocessing_info(self):
        return {
            **super(TranslationStageExperiment, self).make_postprocessing_info(),
            **super(PolarisationFilterExperiment, self).make_postprocessing_info(),
        }
