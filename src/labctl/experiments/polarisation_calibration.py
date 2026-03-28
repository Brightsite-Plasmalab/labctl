from typing_extensions import Unpack
from labctl.devices import ThorlabsRotationStageCmds
from labctl.script import Script
from labctl.experiments.camera import CameraExperiment, CameraExperimentKwargs


# TODO: change the alpha typehint to include np.ndarray of float/int


class PolarisationFilterCalibrationExperimentKwargs(CameraExperimentKwargs):
    alpha: list[float]


class PolarisationFilterCalibrationExperiment(CameraExperiment):
    rotationstage: ThorlabsRotationStageCmds

    def __init__(self, alpha: list[float], **kwargs: Unpack[CameraExperimentKwargs]):
        self.alpha = alpha
        super().__init__(**kwargs)
        self.check_N_frames(
            len(self.alpha), " One configuration for each polarization."
        )

    def make_labctl_header(self):
        cmds = super().make_labctl_header()

        self.rotationstage = ThorlabsRotationStageCmds(cmds)
        cmds.register_device(self.rotationstage, 1)
        return cmds

    def prepare_experiment(self, cmds: Script):
        super().prepare_experiment(cmds)

        self.rotationstage.home()

    def prepare_config(self, cmds, i):
        alphai = self.alpha[i]
        cmds.comment(f"Selecting rotation {i}: {alphai:.3f} degrees")
        self.rotationstage.goto_degrees(alphai)

    def make_postprocessing_info(self):
        info = super().make_postprocessing_info()
        info.update(
            {
                "variable": "polarization_angle",
                "polarization_angle": self.alpha,
            }
        )
        return info
