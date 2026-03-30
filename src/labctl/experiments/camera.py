import math
import enum
from typing import Unpack
import warnings

from typing_extensions import cast, NotRequired
import numpy as np

from labctl.script import Script
from labctl.devices import BncPdgCmds
from labctl.experiments.base import BaseExperiment, BaseExperimentKwargs


class BackgroundConfiguration(enum.IntEnum):
    EVERY_FRAME = 1
    NONE = 0
    BEGIN = -1
    END = -2
    BEGIN_MIDDLE_END = -3
    BEGIN_END = -4

    def make_name_list(self, foreground_num: int) -> list[str]:
        assert (
            foreground_num >= 0
        ), f"foreground_num must be at least 0, got {foreground_num}"
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

    def measurement_count(self, foreground_num) -> int:
        names = self.make_name_list(foreground_num)
        return len(names)

    def index_foreground(self, foreground_num) -> list[int]:
        names = self.make_name_list(foreground_num)
        return (np.asarray(names) == "foreground").nonzero()[0].astype(int)

    def index_background(self, foreground_num) -> list[int]:
        names = self.make_name_list(foreground_num)
        return (np.asarray(names) == "background").nonzero()[0].astype(int)


class CameraExperimentKwargs(BaseExperimentKwargs):
    n_frames: list[int] | int
    t_exposure: float
    camera_delay_optimum: float

    n_iter: NotRequired[int]
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

    In addition, your __init__ method should check whether N_frames is a list of integers, with the correct length.
    """

    pdg: BncPdgCmds

    def __init__(
        self,
        n_frames: list[int] | int,
        t_exposure: float,
        camera_delay_optimum: float,
        *,
        camera_delay_background: float = 0,
        n_iter: int = 1,
        laser_frequency: int = 30,
        camera_channel: str = "C",
        background_every: (
            BackgroundConfiguration | int
        ) = BackgroundConfiguration.EVERY_FRAME,
        camera_reset_time: float = 0.5,
        **kwargs: Unpack[BaseExperimentKwargs],
    ):
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

        if type(self) is CameraExperiment:
            self.check_N_frames(1, "")
        super().__init__(**kwargs)
        self.n_frames: list[int]

    def check_N_frames(self, expected_length: int, config_explanation):
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

    def prepare_experiment(self, cmds: Script):
        """Prepare the experiment. Inherit this method to add more commands."""
        pass

    def get_camera_delay(self, config, version):
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

    def get_camera_delay_foreground(self, config):
        return self.camera_delay_optimum

    def get_camera_delay_background(self, config):
        return self.camera_delay_background

    def perform_measurement(self, cmds: Script, iteration, config, frame, version):
        """Perform a single measurement."""
        cmds.comment(
            f"Acquiring: config {config+1:d}/{len(self.n_frames):d}, {version} ({frame + 1:d}/{self.n_frames[config]:d}), iteration {iteration + 1:d}/{self.n_iter:d}"
        )
        # Get the camera delay for this version (foreground/background)
        cameradelay = self.get_camera_delay(config, version)
        self.pdg.delay(self.camera_channel, cameradelay)

        # Trigger the camera
        self.pdg.arm()

        # Wait for the camera to finish
        cmds.pause((self.t_exposure + self.camera_reset_time) * 1e3)

    def shutdown_experiment(self):
        """Shutdown the experiment. Inherit this method to add more commands."""
        pass

    def make_labctl_script(self) -> Script:
        super().make_labctl_script()  # This will check the config and prepare the experiment
        cmds = self.make_labctl_header()
        self.pdg = cast(BncPdgCmds, list(cmds.devices.keys())[0])

        ###################
        #    PARAMETERS   #
        ###################

        # Acquisition parameters
        T_pulse = 1 / self.laser_frequency  # Pulse period
        N_accumulate = math.floor(1 / T_pulse * self.t_exposure) + 1
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
        self.pdg.channel_gate(self.camera_channel, "LOW")

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

    def get_config_indices(self):
        """
        Returns a list that maps the configurations to the indices of the foreground and background frames in the acquired data.
        [ (fg_idx_config1, bg_idx_config1), (fg_idx_config2, bg_idx_config2), ... ],
        """
        # Initialize a list of empty indices (fg and bg) for each config
        idx = [(np.array([], dtype=int),) * 2] * len(self.n_frames)
        running_total = 0
        for i in range(self.n_iter):
            for j, N_frames_j in enumerate(self.n_frames):
                # For each config, get the indices of the foreground and background frames for this iteration, and add the running total to get the indices in the full acquired data
                fg_idx = (
                    self.background_every.index_foreground(N_frames_j) + running_total
                )
                bg_idx = (
                    self.background_every.index_background(N_frames_j) + running_total
                )

                # Append the indices for this iteration to the total indices for this config
                idx[j] = (
                    np.concatenate((idx[j][0], fg_idx), dtype=int),
                    np.concatenate((idx[j][1], bg_idx), dtype=int),
                )
                running_total += len(fg_idx) + len(bg_idx)

        return idx

    def get_config_index_dict(self):
        """
        Returns a dictionary that maps the config names to the indices of the foreground and background frames in the acquired data.
        { config_name: (fg_idx_config_iter1, bg_idx_config_iter1), ... },
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

    def make_postprocessing_info(self):
        """
        This function creates a dictionary with all necessary information about the experiment to do the postprocessing.
        Most importantly, it creates a list of indices for the foreground and background frames for each config and iteration, which can be used to separate the data during postprocessing.
        """

        conf_idx_dict = self.get_config_index_dict()

        info_obj = {
            "indices": self.get_config_indices(),
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
        f_data, f_pickle=None, info=None
    ) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
        import pickle as pkl
        from toddler.data.spectrum import Spectrum

        if f_pickle is None:
            f_pickle = f_data.with_stem(f_data.stem + "_idx").with_suffix(".pkl")

        # Load pickle file
        if info is None:
            info = pkl.load(open(f_pickle, "rb"))

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
            sig_data = data[:, :, sig_ind[0]]
            bg_data = data[:, :, bg_ind[0]]

            sig_data_avg = sig_data.c.median(axis=2)
            bg_data_avg = bg_data.c.median(axis=2)

            return sig_data, bg_data, sig_data_avg - bg_data_avg

        # Load sif file
        data = Spectrum.from_file(f_data, new_axes=True)
        data._axis_lambda = 0

        # Postprocess all configs
        results = {}
        for i, config in enumerate(info["configs"]):
            results[config] = get_data(data, info, i)

        return results

    def make_postprocessing_script(self):
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
