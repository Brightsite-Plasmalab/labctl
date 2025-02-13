from typing import List
from labctl.experiments.base_camera_experiment import BaseCameraExperiment


class SimpleLaserExperiment(BaseCameraExperiment):

    def get_config_names(self) -> List[str]:
        return [""]

    @classmethod
    def postprocess(cls, f_data, f_pickle=None):
        return list(super().postprocess(f_data, f_pickle).values())[0]
