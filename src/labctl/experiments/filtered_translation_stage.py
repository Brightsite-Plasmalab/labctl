from typing_extensions import Unpack, List
from labctl.experiments.raman_2d import (
    Raman2DExperimentKwargs,
    Raman2DExperiment,
)
from labctl.experiments.translation_stage import (
    TranslationStageExperiment,
    TranslationStageExperimentKwargs,
)


class FilteredTranslationStageExperimentKwargs(
    TranslationStageExperimentKwargs, Raman2DExperimentKwargs
):
    pass


class FilteredTranslationStageExperiment(
    TranslationStageExperiment,
    Raman2DExperiment,
):
    """
    This experiment combines the capabilities of the Raman2DExperiment and the TranslationStageExperiment.
    It will run through all combinations of the translation stage positions and filter stage positions.
    """

    def __init__(self, **kwargs: Unpack[FilteredTranslationStageExperimentKwargs]):
        super().__init__(**kwargs)

    def get_config_order(self):
        N_x = len(self.x)
        N_filter = len(self.filters)
        N_tot = N_x * N_filter

        config_translation = [None] * N_tot
        config_filter = [None] * N_tot

        i = 0
        # Sequentially loop through all translation stage positions
        for i_x in range(N_x):
            # At each translation stage position, loop through all filter positions
            for i_filter in range(N_filter):
                config_translation[i] = i_x
                config_filter[i] = i_filter
                i += 1

        return config_translation, config_filter

    def get_config_names(self) -> List[str]:
        config_names_translation = TranslationStageExperiment.get_config_names(self)
        config_names_filters = Raman2DExperiment.get_config_names(self)

        config_order_translation, config_order_filters = self.get_config_order()
        return [
            f"{config_names_translation[config_order_translation[i]]}_{config_names_filters[config_order_filters[i]]}"
            for i in range(len(config_names_translation))
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
        config_order_translation, config_order_filters = self.get_config_order()
        TranslationStageExperiment.prepare_config(
            self, cmds, config_order_translation[i]
        )
        Raman2DExperiment.prepare_config(self, cmds, config_order_filters[i])


if __name__ == "__main__":
    exp = FilteredTranslationStageExperiment(
        x=[0.0, 1.0, 2.0],
        filters=["bp675", "bp425"],
        n_frames=[1, 1, 1],
        t_exposure=0.1,
        n_iter=1,
        camera_delay_optimum=450e-9,
        dest_folder="/Users/martijn/Downloads/",
        file_name="tmp",
    )
    print(exp.make_labctl_script().print())
