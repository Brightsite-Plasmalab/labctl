"""Camera-based experiment primitives and indexing helpers.

This module contains the generic camera experiment implementation, background
acquisition scheduling, and metadata/index generation used by downstream
postprocessing.
"""

import math
import enum
from typing import Unpack, cast
import warnings
from pathlib import Path

from typing_extensions import NotRequired
import numpy as np

from labctl.script import Script
from labctl.devices import BncPdgCmds
from labctl.experiments.base import BaseExperiment, BaseExperimentKwargs


class BackgroundConfiguration(enum.IntEnum):
    """Background acquisition schedules for camera experiments."""

    EVERY_FRAME = 1
    NONE = 0
    BEGIN = -1
    END = -2
    BEGIN_MIDDLE_END = -3
    BEGIN_END = -4

    def make_name_list(self, foreground_num: int) -> list[str]:
        """Build foreground/background acquisition labels for one config.

        Parameters
        ----------
        foreground_num : int
            Number of foreground acquisitions.

        Returns
        -------
        list[str]
            Sequence containing ``"foreground"`` and ``"background"`` labels.
        """
        if foreground_num < 0:
            msg = f"foreground_num must be at least 0, got {foreground_num}"
            raise ValueError(msg)
        if foreground_num == 0:
            return []

        if self > 0:
            list_out = []
            for i in range(foreground_num):
                list_out.append("foreground")
                if (i + 1) % self == 0:
                    list_out.append("background")
        elif self == BackgroundConfiguration.NONE:
            list_out = ["foreground"] * foreground_num
        elif self == BackgroundConfiguration.BEGIN:
            list_out = ["background"] + ["foreground"] * foreground_num
        elif self == BackgroundConfiguration.END:
            list_out = ["foreground"] * foreground_num + ["background"]
        elif self == BackgroundConfiguration.BEGIN_MIDDLE_END:
            middle_index = foreground_num // 2
            list_out = (
                ["background"]
                + ["foreground"] * middle_index
                + ["background"]
                + ["foreground"] * (foreground_num - middle_index)
                + ["background"]
            )
        elif self == BackgroundConfiguration.BEGIN_END:
            list_out = ["background"] + ["foreground"] * foreground_num + ["background"]
        else:
            msg = f"Invalid BackgroundConfiguration value, should be >0, 0, -1, -2, -3, or -4, got {self.value}"
            raise ValueError(msg)

        return list_out

    def measurement_count(self, foreground_num: int) -> int:
        """Return total measurements for a foreground count.

        Parameters
        ----------
        foreground_num : int
            Number of foreground acquisitions.

        Returns
        -------
        int
            Total acquisitions including background frames.
        """
        names = self.make_name_list(foreground_num)
        return len(names)

    def background_count(self, foreground_num: int) -> int:
        """Return number of scheduled background frames.

        Parameters
        ----------
        foreground_num : int
            Number of foreground acquisitions.

        Returns
        -------
        int
            Number of background acquisitions.
        """
        return self.measurement_count(foreground_num) - foreground_num

    def index_foreground(self, foreground_num: int) -> np.ndarray:
        """Return foreground indices in one acquisition block."""
        names = self.make_name_list(foreground_num)
        return (np.asarray(names) == "foreground").nonzero()[0].astype(int)

    def index_background(self, foreground_num: int) -> np.ndarray:
        """Return background indices in one acquisition block."""
        names = self.make_name_list(foreground_num)
        return (np.asarray(names) == "background").nonzero()[0].astype(int)


class CameraExperimentKwargs(BaseExperimentKwargs):
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


class CameraExperiment(BaseExperiment):
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
        if self.n_iter > 1:
            msg = (
                f"`n_iter` bigger than 1 can cause problems for the standard analysis."
            )
            warnings.warn(msg)

        self.n_frames = n_frames
        self.t_exposure = t_exposure
        self.camera_delay_optimum = camera_delay_optimum
        self.camera_delay_background = camera_delay_background
        self.laser_frequency = laser_frequency
        self.camera_channel = camera_channel
        self.background_every = BackgroundConfiguration(background_every)
        self.camera_reset_time = camera_reset_time
        self.camera_pulse_width = camera_pulse_width

        if type(self) is CameraExperiment:
            self.check_N_frames(1, "")
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
        pass

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

        # Wait for the camera to finish
        cmds.pause(self.t_exposure * 1e3)
        cmds.comment("# Wait for the camera to reset")
        cmds.pause(self.camera_reset_time * 1e3)

    def shutdown_experiment(self) -> None:
        """Shutdown the experiment. Inherit this method to add more commands."""
        pass

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

        self.pdg = cast(BncPdgCmds, list(cmds.devices.keys())[0])

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

        # Setting for camera channel
        self.pdg.channel_gate(self.camera_channel, "LOW")
        self.pdg.channel_mode(self.camera_channel, "BURS")
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
            [
                self.background_every.measurement_count(n) * self.n_iter
                for n in self.n_frames
            ]
        )
        comments = [
            f"Total wait: {cmds.total_wait/1e3/60:.1f}min",
            f"NB: Put the PDG in burst mode",
            f"Kinetic acquisition settings:",
            f"\tExposure time:\t\t{self.t_exposure:.3f}s",
            f"\tAccumulation count:\t1",
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
            "configs": self.get_config_index_dict(),
            # Backwards compatibility
            **dict(
                (f"{config}_sig", conf_idx_dict[config]["foreground"])
                for config in conf_idx_dict
            ),
            **dict(
                (f"{config}_bg", conf_idx_dict[config]["background"])
                for config in conf_idx_dict
            ),
            "n_iter": self.n_iter,
            "n_frames": self.n_frames,
            "t_exposure": self.t_exposure,
            "N_iter": self.n_iter,
            "N_frames": self.n_frames,
            "T_exposure": self.t_exposure,
            "background_every": self.background_every.value,
            **super().make_postprocessing_info(),
        }
        return info_obj

    @staticmethod
    def postprocess(
        f_data,
        f_pickle=None,
        info=None,
    ) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
        """Load and postprocess corrected spectra for each configuration.

        Parameters
        ----------
        f_data : path-like
            Path to the acquired data file.
        f_pickle : path-like, optional
            Path to the metadata pickle. If omitted, derived from ``f_data``.
        info : dict, optional
            Preloaded metadata dictionary.

        Returns
        -------
        dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]
            Mapping from config name to raw signal, raw background, and
            corrected signal.
        """
        import pickle as pkl
        from toddler.data.spectrum import Spectrum

        f_data = Path(f_data)

        if f_pickle is None:
            f_pickle = f_data.with_suffix(".pkl")

        # Load pickle file
        if info is None:
            info = pkl.load(open(f_pickle, "rb"))

        def get_data(data, info, config):
            # Get the keys for the signal and background indices
            sig_key = f"{config}_sig"
            bg_key = f"{config}_bg"

            if not sig_key in info:
                print(f"Warning: No indices found for config {config}, skipping.")
                return None, None

            # Get the indices for the signal and background
            sig_ind = info[sig_key]
            bg_ind = info[bg_key]

            # Get the data for the signal and background
            sig_data = data[:, :, sig_ind]
            bg_data = data[:, :, bg_ind]

            sig_data_avg = sig_data.c.median(axis=2)
            bg_data_avg = bg_data.c.median(axis=2)
            sig_data_processed = (
                sig_data_avg if len(bg_ind) == 0 else sig_data_avg - bg_data_avg
            )

            return sig_data, bg_data, sig_data_processed

        # Load sif file
        data = Spectrum.from_file(f_data, new_axes=True)
        data._axis_lambda = 0
        print(data.shape)

        # Postprocess all configs
        results = {}
        for i, config in enumerate(info["configs"]):
            results[config] = get_data(data, info, config)

        return results, info

    def make_postprocessing_script(self) -> str:
        """Return a legacy postprocessing script template.

        Returns
        -------
        str
            Python source code template for manual postprocessing.
        """
        # TODO: Currently, this will not work! Maybe remove and bundle in package
        code = """
# IMPORTANT: THIS IS NOT CORRECT CODE FOR CURRENT VERSION!!
import pickle
import sif_parser
import numpy as np
import matplotlib.pyplot as plt

f_pickle = ""  # Replace with path of the ..._idx.pkl file
f_data = ""  # Replace with path of the .sif file

# Load pickle file
info = pickle.load(open(f_pickle, "rb"))
print(info.keys())
print(info["configs"])

# Load sif file
print("Loading image data...")
data, _ = sif_parser.np_open(f_data)


def get_data(data, info, config):
    # Get the keys for the signal and background indices
    sig_key = f"{config}_sig"
    bg_key = f"{config}_bg"

    if not sig_key in info:
        return None, None

    # Get the indices for the signal and background
    sig_ind = info[sig_key]
    bg_ind = info[bg_key]

    # Get the data for the signal and background
    sig_data = data[sig_ind[0], :, :]
    bg_data = data[bg_ind[0], :, :]

    sig_data_avg = np.median(sig_data, axis=0)
    bg_data_avg = np.median(bg_data, axis=0)

    return sig_data_avg, bg_data_avg, sig_data_avg - bg_data_avg\n\n
# Load the data of all config
# (sig, bg, sig-bg)\n"""
        for i, config in enumerate(self.get_config_names()):
            if len(self.n_frames) <= i or self.n_frames[i] <= 0:
                continue
            code += f"sig_{config}, bg_{config}, sig_{config}_corr = get_data(data, info, {i})\n"
        return code
