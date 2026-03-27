from typing import Unpack

from build.lib.labctl.experiments.polarisation import PolarisationFilterExperimentKwargs
from build.lib.labctl.experiments.translation_stage import TranslationStageExperimentKwargs
from labctl.script import Script
from labctl.experiments.polarisation import PolarisationFilterExperiment
from labctl.experiments.translation_stage import TranslationStageExperiment


class PolarisedTranslationStageExperimentKwargs(TranslationStageExperimentKwargs, PolarisationFilterExperimentKwargs):
    pass

class PolarisedTranslationStageExperiment(
    PolarisationFilterExperiment, TranslationStageExperiment
):
    def __init__(self, **kwargs: Unpack[PolarisedTranslationStageExperimentKwargs]):
        n_x = len(kwargs["x"])

        # Make sure there are n_x * N_pol (2) configurations.
        # If there are just n_x configurations, repeat each N_pol (2) times.

        if len(kwargs["n_frames"]) == n_x:
            kwargs["n_frames"] = [n for n in kwargs["n_frames"] for _ in range(2)]

        super().__init__(**kwargs)

        if type(self) is PolarisationFilterExperiment:
            self.check_N_frames(2*len(self.x), " Two configurations for each translation position (one for each polarization).")

    def make_labctl_header(self):
        return super().make_labctl_header()
        # super(PolarisationFilterExperiment, self).make_labctl_header()

    def prepare_experiment(self, cmds: Script):
        super(TranslationStageExperiment, self).prepare_experiment(cmds)
        super(PolarisationFilterExperiment, self).prepare_experiment(cmds)

    def prepare_config(self, cmds, i):
        super(TranslationStageExperiment, self).prepare_config(cmds, i // 2)
        super(PolarisationFilterExperiment, self).prepare_config(cmds, i % 2)

    def shutdown_experiment(self):
        super(TranslationStageExperiment, self).shutdown_experiment()
        super(PolarisationFilterExperiment, self).shutdown_experiment()

    def make_postprocessing_info(self):
        dict1 = super(TranslationStageExperiment, self).make_postprocessing_info()
        dict2 = super(PolarisationFilterExperiment, self).make_postprocessing_info()
        total_dict = dict1.update(dict2)
        total_dict['variable'] = ["translation_loc", "alpha"]
        total_dict['alpha'] = total_dict['alpha']*len(total_dict['translation_loc'])
        total_dict['translation_loc'] = [x for x in total_dict['translation_loc'] for _ in range(2)]
        return total_dict
