from typing_extensions import List
from labctl.devices import PiTranslationStage
from labctl.script import Script
from labctl.experiments.base_camera_experiment import BaseCameraExperiment


class TranslationStageExperiment(BaseCameraExperiment):
    x: list[float]
    translationstage: PiTranslationStage

    def __init__(self, x, **kwargs):
        self.x = x
        super().__init__(**kwargs)

    def get_config_names(self) -> List[str]:
        return [f"x_{xi:.3f}mm".replace(".", "_") for xi in self.x]

    def make_labctl_header(self):
        cmds = super().make_labctl_header()

        self.translationstage = PiTranslationStage(cmds)
        cmds.register_device(self.translationstage, 1)

        return cmds

    def prepare_experiment(self, cmds: Script):
        super().prepare_experiment(cmds)

        self.translationstage.stop()
        self.translationstage.SAI()
        self.translationstage.reset_error()
        self.translationstage.set_reference_mode(1, mode="manual")
        self.translationstage.set_servo(1, enable=True)
        self.translationstage.set_position(1, position=0.0)

    def prepare_config(self, cmds, i):
        super().prepare_config(cmds, i)
        xi = self.x[i]
        cmds += f"# Selecting position {i}: {xi:.3f} mm"
        self.translationstage.move_to(axis=1, position=xi)

    def shutdown_experiment(self):
        super().shutdown_experiment()

        self.translationstage.move_to(axis=1, position=0.0)
        self.translationstage.stop()

    def make_postprocessing_info(self):
        return {"x": self.x, **super().make_postprocessing_info()}
