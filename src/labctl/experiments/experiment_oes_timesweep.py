from typing_extensions import List, override
from labctl.experiments.base_camera_experiment import BaseCameraExperiment


class OESTimesweepExperiment(BaseCameraExperiment):
    t0: float
    delta_T: list[int]

    def __init__(self, t0, delta_T, **kwargs):
        self.t0 = t0
        self.delta_T = delta_T
        super().__init__(
            camera_delay_background=0e-9, camera_delay_optimum=0e-9, **kwargs
        )

    @override
    def get_measurement_versions(self):
        return ["foreground"]

    def get_config_names(self) -> List[str]:
        return [f"dt_{ti*1e9:.0f}ns".replace(".", "_") for ti in self.delta_T]

    def make_postprocessing_info(self):
        return {
            "delta_T": self.delta_T,
            "t0": self.t0,
            "t": [ti + self.t0 for ti in self.delta_T],
            **super().make_postprocessing_info(),
        }

    @override
    def get_camera_delay(self, config: int, version: int) -> float:
        return self.t0 + self.delta_T[config]
