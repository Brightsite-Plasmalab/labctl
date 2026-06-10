from typing_extensions import NotRequired

import numpy as np

from .camera_timesweep import CameraTimesweepExperiment
from .base import BaseExperimentKwargs
from .camera import BackgroundConfiguration

class ThorlabsCameraTimesweepExperimentKwargs(BaseExperimentKwargs):
    t_exp: list[float] | np.ndarray
    n_frames: list[int] | int
    t_background: NotRequired[float]
    pulse_width: NotRequired[float]
    repeats: NotRequired[int]

    n_iter: NotRequired[int]
    measurement_frequency: NotRequired[int]
    camera_channel: NotRequired[str]
    background_every: NotRequired[BackgroundConfiguration | int]


class ThorlabsCameraTimesweepExperiment(CameraTimesweepExperiment):
    def __init__(
        self,
        t_exp: list[float] | np.ndarray,
        n_frames: list[int] | int,
        t_background: float = 0.3,
        pulse_width: float = 3e-5,
        *,
        n_iter: int = 1,
        measurement_frequency: int = 30,
        camera_channel: str = "D",
        background_every: (
            BackgroundConfiguration | int
        ) = BackgroundConfiguration.BEGIN_END,
        camera_reset_time: float = 0.5,
        **kwargs: BaseExperimentKwargs
    ):
        delta_t = [t - t_exp[0] for t in t_exp]
        camera_delay_optimum = t_exp[0]
        t_exposure = n_frames / measurement_frequency

        if measurement_frequency > 39.68:
            msg = f"Camera max framerate is 39.68 Hz, got {measurement_frequency} Hz."
            raise ValueError(msg)

        super().__init__(
            delta_t,
            n_frames = n_frames,
            t_exposure = t_exposure,
            camera_delay_optimum = camera_delay_optimum,
            camera_pulse_width = pulse_width,
            camera_delay_background = t_background,
            n_iter = n_iter,
            laser_frequency = measurement_frequency,
            camera_channel = camera_channel,
            background_every = background_every,
            camera_reset_time = camera_reset_time,
            **kwargs
        )

    def make_postprocessing_info(self) -> dict[str, object]:
        info = super().make_postprocessing_info()
        info["repeats"] = self.repeats
        return info