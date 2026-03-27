from typing_extensions import Unpack, List

from labctl.devices import PiTranslationStage
from labctl.script import Script
from labctl.experiments.camera import CameraExperiment, CameraExperimentKwargs


class TranslationStageExperimentKwargs(CameraExperimentKwargs):
    x: list[float]


class TranslationStageExperiment(CameraExperiment):
    translationstage: PiTranslationStage

    def __init__(self, x: list[float] = None, **kwargs):
        if x is None:
            msg = "x must be provided as a keyword argument"
            raise ValueError(msg)
        self.x = x
        super().__init__(**kwargs)
        if type(self) == TranslationStageExperiment:
            self.check_N_frames(len(self.x), " One configuration for each translation position.")

    def make_labctl_header(self):
        cmds = super().make_labctl_header()

        self.translationstage = PiTranslationStage(cmds)
        cmds.register_device(self.translationstage, 2)

        return cmds

    def prepare_experiment(self, cmds: Script):
        super().prepare_experiment(cmds)

        self.translationstage.stop()
        self.translationstage.SAI()
        self.translationstage.reset_error()
        self.translationstage.set_reference_mode(1, mode="manual")
        self.translationstage.set_servo(1, enable=True)
        self.translationstage.set_position(1, position=0.0)

    def get_config_names(self) -> List[str]:
        return [f"x_{xi:.3f}mm".replace(".", "_") for xi in self.x]

    def prepare_config(self, cmds, i):
        super().prepare_config(cmds, i)
        xi = self.x[i]
        cmds.comment(f"Selecting position {i}: {xi:.3f} mm")
        self.translationstage.move_to(axis=1, position=xi)

    def shutdown_experiment(self):
        super().shutdown_experiment()

        self.translationstage.move_to(axis=1, position=0.0)
        self.translationstage.stop()

    def make_postprocessing_info(self):
        info = super().make_postprocessing_info()
        info.update(
            {
                "variable": "translation_loc",
                "translation_loc": self.x,
            }
        )
        return info
