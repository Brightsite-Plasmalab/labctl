"""Core script line container and serialization helpers."""

from __future__ import annotations

from os import PathLike
from typing import Self, Collection
from copy import deepcopy

from typing_extensions import Union


class ScriptBase:
    """Mutable container for labctl script lines."""

    lines: list[str]

    def __init__(self) -> None:
        self.lines = []

    def append(self, commands: Union[str, Collection[str]]) -> None:
        """Append one or many command lines.

        Parameters
        ----------
        commands : str | Collection[str]
            Command string or collection of command strings.
        """
        if isinstance(commands, str):
            self.lines.append(commands + "\n")
        elif isinstance(commands, Collection):
            for x in commands:
                self.append(x)
        else:
            raise Exception(f"Invalid command type: {type(commands)}")

    def print(self) -> None:
        """Print all script lines to standard output."""
        for line in self.lines:
            print(line, end="")

    def write(self, filename: PathLike[str] | str | None) -> None:
        """Write script lines to a file path.

        Parameters
        ----------
        filename : os.PathLike[str] | str | None
            Output file path.
        """
        if filename:
            with open(filename, "w") as f:
                f.writelines(self.lines)

    def copy(self) -> Self:
        """
        Creates a deep copy of the current ScriptBase instance.
        """
        return deepcopy(self)
