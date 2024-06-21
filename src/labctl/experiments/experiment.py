from pathlib import Path
import pickle as pkl


class Experiment:
    author: str
    dest_folder: Path
    prefix: str
    short_explanation: str

    def __init__(
        self,
        author,
        dest_folder,
        prefix,
        short_explanation,
    ):
        self.author = author
        self.dest_folder = Path(dest_folder)
        self.prefix = prefix
        self.short_explanation = short_explanation

    def make_labctl_script(self):
        raise NotImplementedError()

    def make_postprocessing_info(self):
        raise NotImplementedError()

    def make_postprocessing_script(self) -> str:
        raise NotImplementedError()

    def save_labctl_script(self, dest=None):
        if dest is None:
            dest = self.dest_folder / (self.prefix + ".labctl")

        cmds = self.make_labctl_script()
        cmds.write(dest)

        return dest

    def save_postprocessing_script(self, dest=None):
        if dest is None:
            dest = self.dest_folder / (self.prefix + "_process.py")

        script = self.make_postprocessing_script()
        with open(dest, "w") as f:
            f.write(script)

        return dest

    def save_postprocessing_info(self, dest_info=None):
        if dest_info is None:
            dest_info = self.dest_folder / (self.prefix + "_idx.pkl")
        info_obj = self.make_postprocessing_info()

        with open(dest_info, "wb") as f:
            pkl.dump(info_obj, f)

        return dest_info

    def save_all(self):
        self.save_labctl_script()
        self.save_postprocessing_info()
        self.save_postprocessing_script()
