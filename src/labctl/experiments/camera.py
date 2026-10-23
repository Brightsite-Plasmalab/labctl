"""Camera-based experiment primitives and indexing helpers.

This module contains the generic camera experiment implementation, background
acquisition scheduling, and metadata/index generation used by downstream
postprocessing.
"""

import math
import warnings
from abc import ABC
from typing import NotRequired, Unpack, cast

import numpy as np

from labctl.devices import BncPdgCmds
from labctl.experiments import BackgroundConfiguration
from labctl.experiments.base import BaseExperiment, BaseExperimentKwargs
from labctl.script import Script


class BaseCameraExperimentKwargs(BaseExperimentKwargs):
    """Keyword arguments accepted by :class:`CameraExperiment`."""
    n_frames: list[int] | int
    t_exposure: float
    camera_delay_optimum: float

    n_iter: NotRequired[int]
    camera_pulse_width: NotRequired[float]
    laser_frequency: NotRequired[int]
    camera_delay_background: NotRequired[float]
    camera_channel: NotRequired[str]  # Channel for the camera trigger
    background_every: NotRequired[BackgroundConfiguration | int]
    camera_reset_time: NotRequired[float]


class BaseCameraExperiment(BaseExperiment, ABC):
    """
    This experiment takes a series of images with a camera.
    - Changes some experimental configuration.
    - For each configuration, consecutively takes a specified number of foreground and background frames.
    - Repeats the above for a specified number of iterations.

    Attributes
    ----------
    n_iter : int
        Number of iterations to repeat the full set of measurements.
    n_frames : list[int]
        List of number of frames to take for each configuration.
    t_exposure : float
        Exposure time for each frame (in seconds).
    laser_frequency : int
        Frequency of the laser pulses (in Hz).
    camera_delay_optimum : float
        Optimal camera delay for foreground frames (in seconds).
    camera_delay_background : float
        Camera delay for background frames (in seconds).
    camera_channel : str
        Channel used to trigger the camera.
    background_every : BackgroundConfiguration
        Take a background every n frames.
    camera_reset_time: float
        The time to wait after a capture is finished before starting another measurement.

    Notes
    -----
    If you want to have a simple camera experiment with a single configuration, you can use the `SimpleCameraExperiment` class instead.

    When inheriting from this class, the following methods should be implemented:
    - prepare_config: to set the experimental configuration for each measurement.
    - get_config_names: to return the human-readable names of the configurations.

    In addition, your __init__ method should call `check_N_frames`, to check the n_frames.
    """
    pdg: BncPdgCmds
    n_frames: list[int]

    def __init__(
        self,
        n_frames: list[int] | int,
        t_exposure: float,
        camera_delay_optimum: float,
        *,
        camera_pulse_width: float = 1e-5,
        camera_delay_background: float = 0,
        n_iter: int = 1,
        laser_frequency: int = 30,
        camera_channel: str = "C",
        background_every: (
            BackgroundConfiguration | int
        ) = BackgroundConfiguration.EVERY_FRAME,
        camera_reset_time: float = 0.5,
        **kwargs: Unpack[BaseExperimentKwargs],
    ) -> None:
        """Initialize a camera experiment.

        Parameters
        ----------
        n_frames : list[int] | int
            Number of foreground frames per configuration.
        t_exposure : float
            Exposure duration in seconds.
        camera_delay_optimum : float
            Foreground camera trigger delay in seconds.
        camera_delay_background : float, optional
            Background camera trigger delay in seconds.
        n_iter : int, optional
            Number of repeated iterations.
        laser_frequency : int, optional
            Laser pulse frequency in Hz.
        camera_channel : str, optional
            Camera trigger channel name.
        background_every : BackgroundConfiguration | int, optional
            Background acquisition schedule.
        camera_reset_time : float, optional
            Wait time after each frame in seconds.
        camera_pulse_width: float, optional
        **kwargs : Unpack[BaseExperimentKwargs]
            Base experiment metadata.
        """
        self.n_iter = n_iter
        self.n_frames = n_frames
        self.t_exposure = t_exposure
        self.camera_delay_optimum = camera_delay_optimum
        self.camera_delay_background = camera_delay_background
        self.laser_frequency = laser_frequency
        self.camera_channel = camera_channel
        self.background_every = BackgroundConfiguration(background_every)
        self.camera_reset_time = camera_reset_time
        self.camera_pulse_width = camera_pulse_width
        super().__init__(**kwargs)

    def check_N_frames(self, expected_length: int, config_explanation: str) -> None:
        """Check that n_frames has the expected length."""
        if isinstance(self.n_frames, int):
            self.n_frames = [self.n_frames] * expected_length
        if not hasattr(self.n_frames, "__len__"):
            raise TypeError("`N_frames` must be an integer or a collection of integers")
        if len(self.n_frames) != expected_length:
            msg = (
                "Length of `N_frames` must match the number of configurations "
                f"({len(self.n_frames)} != {expected_length}).{config_explanation}"
            )
            raise ValueError(msg)

    def make_labctl_header(self) -> Script:
        """Make the labctl header for the experiment. Inherit this method to add more devices."""
        cmds = Script(title=self.short_explanation, author=self.author)
        cmds.header_info()

        pdg = BncPdgCmds(cmds)

        cmds.register_device(pdg, 0)

        return cmds

    def prepare_experiment(self, cmds: Script) -> None:
        """Prepare the experiment. Inherit this method to add more commands."""

    def get_camera_delay(self, config: int, version: int | str) -> float:
        """Get the camera delay for a specific configuration, frame, and version."""
        if version == 0 or version == "foreground":
            # foreground
            return self.get_camera_delay_foreground(config)
        elif version == 1 or version == "background":
            # background
            return self.get_camera_delay_background(config)
        else:
            msg = f"Unknown version, should be 0/1 or 'foreground'/'background', got {version}"
            raise ValueError(msg)

    def get_camera_delay_foreground(self, config: int) -> float:
        """Return foreground camera delay for a configuration.

        Parameters
        ----------
        config : int
            Configuration index.

        Returns
        -------
        float
            Foreground camera delay in seconds.
        """
        return self.camera_delay_optimum

    def get_camera_delay_background(self, config: int) -> float:
        """Return background camera delay for a configuration.

        Parameters
        ----------
        config : int
            Configuration index.

        Returns
        -------
        float
            Background camera delay in seconds.
        """
        return self.camera_delay_background

    def perform_measurement(
        self,
        cmds: Script,
        iteration: int,
        config: int,
        frame: int,
        version: int | str,
    ) -> None:
        """Perform a single measurement."""
        num_meas = self.background_every.measurement_count(self.n_frames[config])
        cmds.append(f"# Acquiring: config {config+1:d}/{len(self.n_frames):d}, {version} ({frame + 1:d}/{num_meas:d}), "
                    f"iteration {iteration + 1:d}/{self.n_iter:d}")
        # Get the camera delay for this version (foreground/background)
        camera_delay = self.get_camera_delay(config, version)
        self.pdg.delay(self.camera_channel, camera_delay)
        self.pdg.pulsewidth(self.camera_channel, self.camera_pulse_width)

        # Trigger the camera
        self.pdg.arm()

        # Wait for the camera to finish, add one pulse, since first pulse is blocked
        cmds.pause((self.t_exposure + 1/30) * 1e3)
        cmds.comment("# Wait for the camera to reset")
        cmds.pause(self.camera_reset_time * 1e3)

    def shutdown_experiment(self) -> None:
        """Shutdown the experiment. Inherit this method to add more commands."""

    def make_labctl_script(self) -> Script:
        """Generate a complete acquisition script for this experiment.

        Returns
        -------
        Script
            Script containing hardware setup, acquisition loop, and summary
            comments.
        """
        super().make_labctl_script()  # This will check the config and prepare the experiment
        cmds = self.make_labctl_header()
        # for device in cmds.devices:
        #     device.verify_device()

        self.pdg = cast(BncPdgCmds, next(iter(cmds.devices.keys())))

        ###################
        #    PARAMETERS   #
        ###################

        # Acquisition parameters
        T_pulse = 1 / self.laser_frequency  # Pulse period
        N_accumulate = math.floor(self.laser_frequency * self.t_exposure) + 1
        self.t_exposure = (N_accumulate - 0.5) * T_pulse
        print(f"Pulses per frame: {N_accumulate:.0f}")

        cmds.comment(
            f"[N_iter, [N_reps]] = [{self.n_iter}, [{', '.join([str(x) for x in self.n_frames])}]]"
        )

        ###################
        #     COMMANDS    #
        ###################

        self.prepare_experiment(cmds)

        cmds.append("")
        cmds.switch_device(self.pdg)

        # Set Channel G (gate) settings
        # NB: This blocks the first pulse in a burst, which does not reflect new channel settings
        cmds.comment("Channel G - gate")
        self.pdg.enable("G", True)  # Enable channel G
        self.pdg.delay("G", 0e-9)
        self.pdg.sync("G", "T0")
        self.pdg.pulsewidth("G", T_pulse)
        # self.pdg.output("G", "ADJ", voltage=4)  # Output 4V
        self.pdg.polarity("G", "NORM")  # Normal polarity
        self.pdg.channel_mode("G", "SING")
        cmds.pause(100)

        # Setting for camera channel
        self.pdg.channel_gate(self.camera_channel, "LOW")
        # self.pdg.channel_mode(self.camera_channel, "BURS")
        # self.pdg.enable(self.camera_channel, True)  do not enable channel, this will start the pulsing

        # For every iteration of measurements ...
        for i in range(self.n_iter):
            # For every config ...
            for j, N_frames_j in enumerate(self.n_frames):
                cmds.comment(f"Selecting config {j}")
                self.prepare_config(cmds, j)

                # If we don't want to measure this config, skip to the next one
                if N_frames_j == 0:
                    continue

                # Set the desired pulse burst count
                self.pdg.burstcount(self.camera_channel, N_accumulate + 1)

                names = self.background_every.make_name_list(N_frames_j)
                # Repeat for the desired number of frames per batch
                for k, name in enumerate(names):
                    self.perform_measurement(cmds, i, j, k, name)

        self.shutdown_experiment()

        # Write initialization file
        # cmds.print()
        n_total = sum(
            self.background_every.measurement_count(n) * self.n_iter
                for n in self.n_frames
        )
        comments = [
            f"Total wait: {cmds.total_wait/1e3/60:.1f}min",
            "NB: Put the PDG in burst mode",
            "Kinetic acquisition settings:",
            f"\tExposure time:\t\t{self.t_exposure:.3f}s",
            "\tAccumulation count:\t1",
            f"\tFrame count:\t\t{n_total}",
        ]

        for comment in comments:
            print(comment)
            cmds.comment(comment)

        return cmds

    def get_config_indices_full(self) -> list[list[tuple[np.ndarray, np.ndarray]]]:
        """Return per-iteration foreground/background indices for each config.

        Returns
        -------
        list[list[tuple[np.ndarray, np.ndarray]]]
            Nested list indexed as ``[iteration][config]`` with foreground and
            background index arrays.
        """
        idx = [[] for _ in range(self.n_iter)]

        running_total = 0
        for i in range(self.n_iter):
            for j, N_frames_j in enumerate(self.n_frames):
                # For each config, get the indices of the foreground and background frames for this iteration, and add the running total to get the indices in the full acquired data
                fg_idx = self.background_every.index_foreground(N_frames_j) + running_total
                bg_idx = self.background_every.index_background(N_frames_j) + running_total

                # Append the indices for this iteration to the total indices for this config
                idx[i].append((fg_idx, bg_idx))

                running_total += len(fg_idx) + len(bg_idx)
        return idx

    def get_config_indices(self) -> list[list[np.ndarray]]:
        """Return grouped foreground/background indices for each config.

        Returns
        -------
        list[list[np.ndarray]]
            Per-config foreground/background arrays with all iterations
            concatenated.
        """
        full_indices = self.get_config_indices_full()
        idx = [[] for _ in range(len(self.n_frames))]
        for j in range(len(self.n_frames)):
            for k in (0, 1):
                vals = [full_indices[i][j][k] for i in range(self.n_iter)]
                idx[j].append(np.concatenate(vals))
        return idx

    def get_config_index_dict(self) -> dict[str, dict[str, np.ndarray]]:
        """Return grouped indices keyed by human-readable config name.

        Returns
        -------
        dict[str, dict[str, np.ndarray]]
            Mapping of config names to ``foreground`` and ``background`` arrays.
        """
        idx = self.get_config_indices()
        config_names = self.get_config_names()

        idx_dict = {}
        for i, config_name in enumerate(config_names):
            idx_dict[config_name] = {
                "foreground": idx[i][0],
                "background": idx[i][1],
            }

        return idx_dict

    def make_postprocessing_info(self) -> dict[str, object]:
        """
        This function creates a dictionary with all necessary information about the experiment to do the postprocessing.
        Most importantly, it creates a list of indices for the foreground and background frames for each config and iteration, which can be used to separate the data during postprocessing.
        """

        conf_idx_dict = self.get_config_index_dict()

        info_obj = {
            "indices": self.get_config_indices(),
            "indices_full": self.get_config_indices_full(),
            "configs": conf_idx_dict,
            # Backwards compatibility
            **{
                f"{config}_sig": conf_idx_dict[config]["foreground"]
                for config in conf_idx_dict
            },
            **{
                f"{config}_bg": conf_idx_dict[config]["background"]
                for config in conf_idx_dict
            },
            "n_iter": self.n_iter,
            "n_frames": self.n_frames,
            "t_exposure": self.t_exposure,
            "N_iter": self.n_iter,
            "N_frames": self.n_frames,
            "T_exposure": self.t_exposure,
            "background_every": self.background_every.value,
            "camera_delay_optimum": self.camera_delay_optimum,
            "camera_delay_background": self.camera_delay_background,
            **super().make_postprocessing_info(),
        }
        return info_obj