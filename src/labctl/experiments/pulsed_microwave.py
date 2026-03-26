from abc import abstractmethod

from typing_extensions import Unpack

from labctl.script import Script
from labctl.experiments.camera import CameraExperiment, CameraExperimentKwargs
import re


class PulsedMicrowaveTimesweepKwargs(CameraExperimentKwargs):
    MW_pulse_frequency: int  # Frequency of the microwave pulse
    channel_MW_trigger: str  # Channel of the microwave trigger
    t0: float  # Time delay such that the start of the laser pulse synchronizes with the start of the microwave pulse,
    # should be ~100ns
    delta_t: list[float]  # List of time delays to sweep, relative to t0


class PulsedMicrowaveTimesweep(CameraExperiment):
    """
    This experiment sweeps the delay of a pulsed microwave signal with respect to the laser (and camera).

    NB:
    - The microwave pulse frequency should be a multiple of the laser frequency
    """
    channel_MW_trigger_int: int  # Channel of the microwave trigger

    def __init__(self, t0: float, delta_t: list[float], MW_pulse_frequency: int, channel_MW_trigger: str,
                 **kwargs: Unpack[CameraExperimentKwargs]):
        self.t0 = t0
        self.delta_t = delta_t
        self.channel_MW_trigger = channel_MW_trigger  # Should be in [A, B, ..., H]
        self.channel_MW_trigger_int = (
            ord(channel_MW_trigger) - ord("A") + 1
        )  # Channel A -> 0, B -> 1, ...

        # Perform some checks to see if all inputs are valid
        if self.channel_MW_trigger_int < 3 or self.channel_MW_trigger_int > 8:
            raise ValueError(f"Invalid channel {channel_MW_trigger}, should be in [D, E, F, G, H]")
        self.MW_pulse_frequency = MW_pulse_frequency

        if (self.MW_pulse_frequency % self.laser_frequency != 0) or (self.MW_pulse_frequency == self.laser_frequency):
            msg = (f"The microwave pulse frequency should be a multiple of the laser frequency "
                   f"({self.laser_frequency}Hz). The closest multiple is "
                   f"{self.laser_frequency * round(self.MW_pulse_frequency / self.laser_frequency)}Hz")
            raise ValueError(msg)
        multiple = self.MW_pulse_frequency // self.laser_frequency

        print(f"The microwave pulse frequency is {self.MW_pulse_frequency} Hz")

        T0_str = f"{1/self.MW_pulse_frequency:,.10f}"
        # add space every 3 digits after the decimal point
        T0_str = re.sub(r"((?<=\.\d{3})|(?<=\.\d{6})|(?<=\.\d{9}))(\d)", r" \2", T0_str)
        print(f"Microwave pulse delay generator:")
        print(f"\t T0: {T0_str} s")
        print(f"\t Burst count: {multiple}")
        print(f"Channel {self.channel_MW_trigger} is used for the MW trigger")
        print(f"\t and synchronizes the start of the MW to the laser at t0 = {int(self.t0*1e9):_d} ns")
        print("\n")

        super().__init__(**kwargs, camera_delay_background=0)
        self.check_N_frames(len(self.delta_t), " One configuration for each time delay value.")

    def make_postprocessing_info(self):
        info = super().make_postprocessing_info()
        info.update({
            "variable": "t",
            "delta_t": self.delta_t,
            "t0": self.t0,
            "t": [ti + self.t0 for ti in self.delta_t],
        })
        return info

    def get_mw_delay(self, i):
        delay = self.t0 - self.delta_t[i]
        if delay < -900e-6:
            delay += 1 / self.MW_pulse_frequency
        return delay

    def prepare_config(self, cmds: Script, i):
        """Prepares experimental configuration i."""
        self.pdg.delay(self.channel_MW_trigger_int, self.get_mw_delay(i))
        cmds.pause(1000)

    def get_camera_delay_foreground(self, config):
        return self.camera_delay_optimum

    def get_camera_delay_background(self, config):
        # Take the background one microwave pulse after the laser pulse
        return self.camera_delay_optimum + 1 / self.MW_pulse_frequency

    def shutdown_experiment(self):
        """Shutdown the experiment. Inherit this method to add more commands."""
        pass
