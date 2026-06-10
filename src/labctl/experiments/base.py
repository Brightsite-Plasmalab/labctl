"""Base abstractions for experiment script generation and persistence."""

import os
import pathlib
import pickle as pkl
from collections.abc import Sequence
from typing import TypedDict
from abc import ABC, abstractmethod

from typing_extensions import NotRequired
import numpy as np


class BaseExperimentKwargs(TypedDict):
    """Shared keyword arguments accepted by experiment constructors."""
    dest_folder: os.PathLike | str
    file_name: str
    author: NotRequired[str]
    short_explanation: NotRequired[str]


class BaseExperiment(ABC):
    """Abstract base class for all experiments."""

    def __init__(
        self,
        dest_folder: os.PathLike | str,
        file_name: str,
        author: str = "",
        short_explanation: str = "",
    ) -> None:
        """Initialize common experiment metadata.

        Parameters
        ----------
        dest_folder : os.PathLike | str
            Output folder for generated scripts and metadata.
        file_name : str
            Base name used for output artifacts.
        author : str, optional
            Author name written to metadata.
        short_explanation : str, optional
            Human-readable experiment description.
        """
        self.author = author
        self.dest_folder = pathlib.Path(dest_folder)
        self.file_name = file_name
        self.short_explanation = short_explanation

    @abstractmethod
    def make_labctl_script(self):
        """Build the lab control script for the experiment.

        Returns
        -------
        Script
            Concrete script object containing all commands.
        """
        pass

    @abstractmethod
    def prepare_config(self, cmds, i: int) -> None:
        """Prepares experimental configuration i."""
        pass

    @abstractmethod
    def get_config_names(self) -> list[str]:
        """Get the human-readable names of the configurations."""
        pass

    def make_postprocessing_info(self) -> dict[str, object]:
        """Build common postprocessing metadata.

        Returns
        -------
        dict[str, object]
            Base metadata shared by all experiments.
        """
        info_obj = {
            "file_name": self.file_name,
            "short_explanation": self.short_explanation,
            "author": self.author,
            "experiment_type": type(self).__name__,
            "version": "0.0.2",
        }
        # def to_list(value):
        #     if isinstance(value, np.ndarray):
        #         return value.tolist()
        #     elif isinstance(value, Sequence) and not isinstance(value, str):
        #         return to_list(value)
        #     return value
        #
        # for key, value in info_obj.items():
        #     info_obj[key] = to_list(info_obj[key])


        return info_obj

    @abstractmethod
    def make_postprocessing_script(self) -> str:
        """Build a helper postprocessing script.

        Returns
        -------
        str
            Python source code for postprocessing.
        """
        pass

    def save_labctl_script(self, dest: os.PathLike | str | None = None):
        """Generate and persist the labctl script.

        Parameters
        ----------
        dest : os.PathLike | str | None, optional
            Destination path. Defaults to ``<dest_folder>/<file_name>.labctl``.

        Returns
        -------
        os.PathLike | str
            Path where the script was written.
        """
        if dest is None:
            dest = self.dest_folder / (self.file_name + ".labctl")

        cmds = self.make_labctl_script()
        cmds.write(dest)

        return dest

    def save_postprocessing_script(self, dest: os.PathLike | str | None = None):
        """Generate and persist the postprocessing script.

        Parameters
        ----------
        dest : os.PathLike | str | None, optional
            Destination path. Defaults to
            ``<dest_folder>/<file_name>_process.py``.

        Returns
        -------
        os.PathLike | str
            Path where the script was written.
        """
        if dest is None:
            dest = self.dest_folder / (self.file_name + "_process.py")

        script = self.make_postprocessing_script()
        with open(dest, "w") as f:
            f.write(script)

        return dest

    def save_postprocessing_info(
        self,
        dest_info: os.PathLike | str | None = None,
    ) -> pathlib.Path | os.PathLike | str:
        """Persist postprocessing metadata as a pickle file.

        Parameters
        ----------
        dest_info : os.PathLike | str | None, optional
            Destination path. Defaults to ``<dest_folder>/<file_name>.pkl``.

        Returns
        -------
        os.PathLike | str
            Path where metadata was written.
        """
        if dest_info is None:
            dest_info = self.dest_folder / (self.file_name + ".pkl")
        info_obj = self.make_postprocessing_info()

        with open(dest_info, "wb") as f:
            pkl.dump(info_obj, f)

        return dest_info

    def save_all(self) -> None:
        """Save script, metadata, and postprocessing helper script."""
        self.save_labctl_script()
        self.save_postprocessing_info()
        self.save_postprocessing_script()
