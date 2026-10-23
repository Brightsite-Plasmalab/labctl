import enum

import numpy as np


class BackgroundConfiguration(enum.IntEnum):
    """
    Background acquisition schedules for camera experiments.

    All positive enum values ``N`` schedule one background frame every ``N``
    foreground frames.
    Zero skips taking any background frames.
    Negative values have special meanings:

    .. list-table::
       :header-rows: 1

       * - Value
         - Name
         - Meaning
       * - ``-1``
         - ``BEGIN``
         - Add one background frame before all foreground frames.
       * - ``-2``
         - ``END``
         - Add one background frame after all foreground frames.
       * - ``-3``
         - ``BEGIN_MIDDLE_END``
         - Add one background frame at the beginning, middle, and end.
       * - ``-4``
         - ``BEGIN_END``
         - Add one background frame at both the beginning and end.
       * - ``-5``
         - ``BEGIN_MIDDLE``
         - Add one background frame at the beginning and middle.
       * - ``-6``
         - ``MIDDLE``
         - Add one background frame at the middle split of the foreground block.
       * - ``-7``
         - ``MIDDLE_END``
         - Add one background frame at the middle and end.

    """
    EVERY_FRAME = 1
    """Insert a background frame after every foreground frame."""
    NONE = 0
    """Do not schedule background frames."""
    BEGIN = -1
    """Add one background frame before all foreground frames."""
    END = -2
    """Add one background frame after all foreground frames."""
    BEGIN_MIDDLE_END = -3
    """Add one background frame at the beginning, middle, and end."""
    BEGIN_END = -4
    """Add one background frame at both the beginning and end."""
    BEGIN_MIDDLE = -5
    """Add one background frame at the beginning and middle."""
    MIDDLE = -6
    """Add one background frame at the middle split of the foreground block."""
    MIDDLE_END = -7
    """Add one background frame at the middle and end."""

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

        # Positive values mean "insert a background every N foreground frames".
        if self > 0:
            out: list[str] = []
            for i in range(1, foreground_num + 1):
                out.append("foreground")
                if (i + 1) % int(self) == 0:
                    out.append("background")
            return out

        BC = BackgroundConfiguration
        match self:
            case BC.NONE:
                return ["foreground"] * foreground_num

            case BC.BEGIN:
                return ["background"] + ["foreground"] * foreground_num

            case BC.MIDDLE:
                middle_index = foreground_num // 2
                return (
                        ["foreground"] * middle_index
                        + ["background"]
                        + ["foreground"] * (foreground_num - middle_index)
                )

            case BC.END:
                return ["foreground"] * foreground_num + ["background"]

            case BC.BEGIN_END:
                return ["background"] + ["foreground"] * foreground_num + ["background"]

            case BC.BEGIN_MIDDLE_END:
                return (
                        ["background"]
                        + BC.MIDDLE.make_name_list(foreground_num)
                        + ["background"]
                )

            case BC.BEGIN_MIDDLE:
                return ["background"] + BC.MIDDLE.make_name_list(foreground_num)

            case BC.MIDDLE_END:
                return BC.MIDDLE.make_name_list(foreground_num) + ["background"]

            case _:
                msg = (
                    "Invalid BackgroundConfiguration value, expected > 0 or one of "
                    "{0, -1, -2, -3, -4, -5, -6, -7}, "
                    f"got {self.value}"
                )
                raise ValueError(msg)

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