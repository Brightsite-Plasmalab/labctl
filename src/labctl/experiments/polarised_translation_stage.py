from typing_extensions import List
from labctl.devices import PiTranslationStage
from labctl.script import Script
from labctl.experiments.polarisation import PolarisationFilterExperiment
from labctl.experiments.translation_stage import TranslationStageExperiment


class PolarisedTranslationStageExperiment(
    PolarisationFilterExperiment, TranslationStageExperiment
):
    def __init__(self, **kwargs):
        N_x = len(kwargs.get("x", []))
        N_pol = 2

        # Make sure there are N_x * N_pol configurations.
        # If there are just N_x configurations, repeat each N_pol times.

        if len(kwargs.get("N_frames", [])) == N_x:
            kwargs["N_frames"] = [n for n in kwargs["N_frames"] for _ in range(N_pol)]
        assert (
            len(kwargs.get("N_frames", [])) == N_x * N_pol
        ), "N_frames should have length N_x * N_pol"

        super().__init__(**kwargs)
        # TranslationStageExperiment.__init__(self, x, **kwargs)
        # PolarisationFilterExperiment.__init__(
        #     self, alpha_ver=alpha_ver, alpha_hor=alpha_hor, **kwargs
        # )

    def get_config_names(self) -> List[str]:
        config_names_translation = TranslationStageExperiment.get_config_names(self)
        config_names_polarisation = PolarisationFilterExperiment.get_config_names(self)
        print(config_names_polarisation, config_names_translation)
        return [
            f"{cn_t}_{cn_p}"
            for cn_t in config_names_translation
            for cn_p in config_names_polarisation
        ]

    def make_labctl_header(self):
        return super().make_labctl_header()
        # super(PolarisationFilterExperiment, self).make_labctl_header()

    def prepare_experiment(self, cmds: Script):
        super(TranslationStageExperiment, self).prepare_experiment(cmds)
        super(PolarisationFilterExperiment, self).prepare_experiment(cmds)

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
