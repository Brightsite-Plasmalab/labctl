import os
import pathlib
import pickle as pkl
from typing import TypedDict
from abc import ABC, abstractmethod

from typing_extensions import NotRequired


class BaseExperimentKwargs(TypedDict):
    dest_folder: os.PathLike | str
    file_name: str
    author: NotRequired[str]
    short_explanation: NotRequired[str]


class BaseExperiment(ABC):
    def __init__(
        self,
        dest_folder: os.PathLike | str,
        file_name: str,
        author: str = "",
        short_explanation: str = "",
    ):
        self.author = author
        self.dest_folder = pathlib.Path(dest_folder)
        self.file_name = file_name
        self.short_explanation = short_explanation

    @abstractmethod
    def make_labctl_script(self):
        pass

    @abstractmethod
    def prepare_config(self, cmds, i):
        """Prepares experimental configuration i."""
        pass

    def make_postprocessing_info(self):
        info_obj = {
            "file_name": self.file_name,
            "short_explanation": self.short_explanation,
            "author": self.author,
            "experiment_type": type(self).__name__,
            "version": "0.0.2",
        }
        return info_obj

    @abstractmethod
    def make_postprocessing_script(self) -> str:
        pass  # TODO: question, isn't bundling analysis into package easier/better?

    def save_labctl_script(self, dest=None):
        if dest is None:
            dest = self.dest_folder / (self.file_name + ".labctl")

        cmds = self.make_labctl_script()
        cmds.write(dest)

        return dest

    def save_postprocessing_script(self, dest=None):
        if dest is None:
            dest = self.dest_folder / (self.file_name + "_process.py")

        script = self.make_postprocessing_script()
        with open(dest, "w") as f:
            f.write(script)

        return dest

    def save_postprocessing_info(self, dest_info=None):
        if dest_info is None:
            dest_info = self.dest_folder / (self.file_name + ".pkl")
        info_obj = self.make_postprocessing_info()

        with open(dest_info, "wb") as f:
            pkl.dump(info_obj, f)

        return dest_info

    def save_all(self):
        self.save_labctl_script()
        self.save_postprocessing_info()
        self.save_postprocessing_script()
