from typing import cast

from typing_extensions import NotRequired, Unpack
from labctl.devices import ThorlabsRotationStageCmds
from labctl.experiments import PolarisationFilterSweepExperiment
from labctl.experiments.polarisation_sweep import PolarisationFilterSweepExperimentKwargs
from labctl.experiments.camera import CameraExperimentKwargs


class PolarisationFilterExperimentKwargs(CameraExperimentKwargs):
    alpha_ver: float
    alpha_hor: NotRequired[float]


class PolarisationFilterExperiment(PolarisationFilterSweepExperiment):
    rotationstage: ThorlabsRotationStageCmds
    alpha_ver: float
    alpha_hor: float

    def __init__(
        self,
        alpha_ver: float = None,
        alpha_hor: float = None,
        **kwargs: Unpack[CameraExperimentKwargs],
    ):
        if alpha_ver is None:
            msg = "alpha_ver must be provided as a (keyword) argument"
            raise ValueError(msg)
        self.alpha_ver = alpha_ver
        if alpha_hor is None:
            alpha_hor = alpha_ver + 90.0
        self.alpha_hor = alpha_hor

        kwargs = cast(PolarisationFilterSweepExperimentKwargs, kwargs)
        kwargs['alpha'] = [alpha_ver, alpha_hor]

        super().__init__(**kwargs)
        if type(self) is PolarisationFilterExperiment:
            self.check_N_frames(2, " One configuration for each polarization.")

    def get_config_names(self) -> list[str]:
        return ["ver", "hor"]

    def prepare_config(self, cmds, i):
        names = ["vertical", "horizontal"]
        cmds.append(f"# Selecting {names[i]} rotation")
        super().prepare_config(cmds, i)

    def make_postprocessing_info(self):
        info = super().make_postprocessing_info()
        info.update(
            {
                "alpha_ver": self.alpha_ver,
                "alpha_hor": self.alpha_hor,
            }
        )
        return info
