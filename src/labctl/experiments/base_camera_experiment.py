import math
from typing import List, cast
import numpy as np
from labctl.script import Script
from labctl.devices import BncPdgCmds
from labctl.experiments.experiment import Experiment
from abc import abstractmethod


class BaseCameraExperiment(Experiment):
    """
    This experiment takes a series of images with a camera.
    - Changes some experimental configuration.
    - For each configuration, consecutively takes a specified number of foreground and background frames.
    - Repeats the above for a specified number of iterations."""

    N_iter: int
    N_frames: list[int]
    T_exposure: float
    laser_frequency: int
    camera_delay_optimum: float
    camera_delay_background: float
    camera_channel: str = "C"  # Channel for the camera trigger

    pdg: BncPdgCmds

    def __init__(
        self,
        N_iter,
        N_frames,
        T_exposure,
        camera_delay_optimum,
        camera_delay_background=0e-9,
        laser_frequency=30,
        camera_channel="C",
        **kwargs,
    ):
        self.N_iter = N_iter
        self.N_frames = N_frames
        self.T_exposure = T_exposure
        self.camera_delay_optimum = camera_delay_optimum
        self.camera_delay_background = camera_delay_background
        self.laser_frequency = laser_frequency
        self.camera_channel = camera_channel

        super().__init__(**kwargs)

        assert len(N_frames) == len(
            self.get_config_names()
        ), "N_frames should have the same length as the number of configurations"

    @abstractmethod
    def get_config_names(self) -> List[str]:
        """Get the human-readable names of the configurations."""
        pass

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

    @abstractmethod
    def prepare_config(self, cmds, i):
        """Prepares experimental configuration i."""
        pass

    def get_measurement_versions(self):
        return ["foreground", "background"]

    def get_camera_delay(self, config, version):
        """Get the camera delay for a specific configuration, frame, and version."""
        if version == 0:
            # foreground
            return self.camera_delay_optimum
        else:
            # background
            return self.camera_delay_background

    def perform_measurement(self, cmds, iteration, config, frame, version):
        """Perform a single measurement."""
        cmds += f"# Acquiring: config {config+1:d}/{len(self.N_frames):d}, {self.get_measurement_versions()[version]} ({frame+1:d}/{self.N_frames[config]:d}), iteration {iteration+1:d}/{self.N_iter:d}"

        # Get the camera delay for this version (foreground/background)
        cameradelay = self.get_camera_delay(config, version)
        self.pdg.delay(self.camera_channel, cameradelay)

        # Trigger the camera
        self.pdg.arm()

        # Wait for the camera to finish
        cmds.pause((self.T_exposure + 0.5) * 1e3)

    def shutdown_experiment(self):
        """Shutdown the experiment. Inherit this method to add more commands."""
        pass

    def make_labctl_script(self) -> Script:
        cmds = self.make_labctl_header()
        self.pdg = cast(BncPdgCmds, list(cmds.devices.keys())[0])

        ###################
        #    PARAMETERS   #
        ###################

        # Acquisition parameters
        T_pulse = 1 / self.laser_frequency  # Pulse period
        N_accumulate = math.floor(1 / T_pulse * self.T_exposure) + 1
        self.T_exposure = (N_accumulate - 0.5) * T_pulse
        print(f"Pulses per frame: {N_accumulate:.0f}")

        cmds += f"# [N_iter, [N_reps]] = [{self.N_iter}, [{', '.join([str(x) for x in self.N_frames])}]]"

        N_total = sum([2 * N * self.N_iter for N in self.N_frames])

        ###################
        #     COMMANDS    #
        ###################

        self.prepare_experiment(cmds)

        cmds += ""
        cmds.switch_device(self.pdg)

        # Set Channel G (gate) settings
        # NB: This blocks the first pulse in a burst, which does not reflect new channel settings
        cmds += [
            "# Channel G - gate",
        ]
        self.pdg.enable("G", True)  # Enable channel G
        self.pdg.delay("G", 0e-9)
        self.pdg.sync("G", "T0")
        self.pdg.pulsewidth("G", T_pulse)
        # self.pdg.output("G", "ADJ", voltage=4)  # Output 4V
        self.pdg.polarity("G", "NORM")  # Normal polarity
        self.pdg.channel_mode("G", "SING")
        self.pdg.channel_gate(self.camera_channel, "LOW")

        # For every iteration of measurements ...
        for i in range(self.N_iter):
            # For every config ...
            for j, N_frames_j in enumerate(self.N_frames):
                cmds += f"# Selecting config {j}"
                self.prepare_config(cmds, j)

                # If we don't want to measure this config, skip to the next one
                if N_frames_j == 0:
                    continue

                # Set the desired pulse burst count
                self.pdg.burstcount(self.camera_channel, N_accumulate + 1)

                # Repeat for the desired number of frames per batch
                for k in range(N_frames_j):
                    # First do a burst for the foreground, then one for the background.
                    for l, _ in enumerate(self.get_measurement_versions()):
                        self.perform_measurement(cmds, i, j, k, l)

        self.shutdown_experiment()

        # Write initialization file
        # cmds.print()
        comments = [
            f"Total wait: {cmds.total_wait/1e3/60:.1f}min",
            f"NB: Put the PDG in burst mode",
            f"Kinetic acquisition settings:",
            f"\tExposure time:\t\t{self.T_exposure:.2f}s",
            f"\tAccumulation count:\t1",
            f"\tFrame count:\t\t{N_total}",
        ]

        for comment in comments:
            print(comment)
            cmds += "# " + comment

        return cmds

    def make_postprocessing_info(self):
        sigs = []
        for i in range(self.N_iter):
            for j, f in enumerate(self.N_frames):
                for k in range(f):
                    for l in range(2):
                        sigs.append((-l * 2 + 1) * (j + 1))
        sigs = np.array(sigs)

        idx = [
            [np.where(sigs == i + 1), np.where(sigs == -(i + 1))]
            for i in range(len(self.N_frames))
        ]

        info_obj = {
            "indices": idx,
            **dict(
                (f"{i}_{'sig' if j==0 else 'bg'}", idx[i][j])
                for i in range(len(self.N_frames))
                for j in range(2)
            ),
            **dict(
                (f"{self.get_config_names()[i]}_{'sig' if j==0 else 'bg'}", idx[i][j])
                for i in range(len(self.N_frames))
                for j in range(2)
            ),
            "prefix": self.prefix,
            "short_explanation": self.short_explanation,
            "author": self.author,
            "configs": self.get_config_names(),
            "N_iter": self.N_iter,
            "N_frames": self.N_frames,
            "T_exposure": self.T_exposure,
        }
        return info_obj

    def postprocess(f_data, f_pickle=None, info=None):
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
        data = Spectrum.from_file(f_data)
        data._axis_lambda = 0

        # Postprocess all configs
        results = {}
        for i, config in enumerate(info["configs"]):
            results[config] = get_data(data, info, i)

        return results

    def make_postprocessing_script(self):
        code = """import pickle
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
            if len(self.N_frames) <= i or self.N_frames[i] <= 0:
                continue
            code += f"sig_{config}, bg_{config}, sig_{config}_corr = get_data(data, info, {i})\n"
        return code
