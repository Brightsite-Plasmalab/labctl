from typing_extensions import List
from labctl.experiments.base_camera_experiment import BaseCameraExperiment
from abc import abstractmethod
from labctl.script import Script
from labctl.experiments.base_camera_experiment import BaseCameraExperiment
import re


class LaserPulsedMicrowaveTimesweep(BaseCameraExperiment):
    """
    This experiment sweeps the delay of a pulsed microwave signal with respect to the laser (and camera).

    NB:
    - The microwave pulse frequency should be a multiple of the laser frequency
    """

    MW_pulse_frequency: int  # Frequency of the microwave pulse
    channel_MW_trigger: str  # Channel of the microwave trigger
    channel_MW_trigger_int: int  # Channel of the microwave trigger
    t0: float  # Time delay such that the start of the laser pulse synchronises with the start of the microwave pulse, should be ~100ns
    delta_T: list[int]  # List of time delays to sweep, relative to t0

    def __init__(self, t0, delta_T, MW_pulse_frequency, channel_MW_trigger, **kwargs):
        self.t0 = t0
        self.delta_T = delta_T
        self.channel_MW_trigger = channel_MW_trigger  # Should be in [A, B, ..., H]
        self.channel_MW_trigger_int = (
            ord(channel_MW_trigger) - ord("A") + 1
        )  # Channel A -> 0, B -> 1, ...

        # Perform some checks to see if all inputs are valid
        assert self.channel_MW_trigger_int in range(
            1, 9
        ), f"Invalid channel {channel_MW_trigger}, should be in [A, B, ..., H]"
        assert self.channel_MW_trigger_int not in [
            1,
            2,
            3,
        ], "Channels A,B,C are reserved for the laser and camera. Please be careful with the trigger channel!"
        self.MW_pulse_frequency = MW_pulse_frequency

        assert (
            self.MW_pulse_frequency % self.laser_frequency == 0
        ), f"The microwave pulse frequency should be a multiple of the laser frequency ({self.laser_frequency}Hz). The closest multiple is {self.laser_frequency * round(self.MW_pulse_frequency / self.laser_frequency)}Hz"
        multiple = self.MW_pulse_frequency // self.laser_frequency
        if multiple <= 1:
            print(
                f"Running at {self.laser_frequency}Hz makes it impossible to get a background signal. Beware, and think of a different method for acquiring the background, such as a separate measurement with the laser off."
            )

        print(f"The microwave pulse frequency is {self.MW_pulse_frequency} Hz")

        T0_str = f"{1/self.MW_pulse_frequency:,.10f}"
        T0_str = re.sub(r"((?<=\.\d{3})|(?<=\.\d{6})|(?<=\.\d{9}))(\d)", r" \2", T0_str)
        print(f"Microwave pulse delay generator:")
        print(f"\t T0: {T0_str} s")
        print(f"\t Burst count: {multiple}")
        print(f"Channel {self.channel_MW_trigger} is used for the MW trigger")
        print(
            f"\t and synchronizes the start of the MW to the laser at t0 = {int(self.t0*1e9):_d} ns"
        )
        print("\n")

        super().__init__(**kwargs, camera_delay_background=None)

    def get_config_names(self) -> List[str]:
        return [f"dt_{ti*1e9:.0f}ns".replace(".", "_") for ti in self.delta_T]

    def make_postprocessing_info(self):
        return {
            "delta_T": self.delta_T,
            "t0": self.t0,
            "t": [ti + self.t0 for ti in self.delta_T],
            **super().make_postprocessing_info(),
        }

    def get_mw_delay(self, i):
        delay = self.t0 - self.delta_T[i]
        if delay < -900e-6:
            delay += 1 / self.MW_pulse_frequency
        return delay

    @abstractmethod
    def prepare_config(self, cmds: Script, i):
        """Prepares experimental configuration i."""
        self.pdg.delay(self.channel_MW_trigger_int, self.get_mw_delay(i))
        cmds.pause(1000)
        pass

    def get_camera_delay(self, config, version):
        """Get the camera delay for a specific configuration, frame, and version."""
        if version == 0:
            # foreground
            return self.camera_delay_optimum
        else:
            # background
            # Take the background one microwave pulse after the laser pulse
            return self.camera_delay_optimum + 1 / self.MW_pulse_frequency

    def shutdown_experiment(self):
        """Shutdown the experiment. Inherit this method to add more commands."""
        pass
