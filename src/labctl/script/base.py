from __future__ import annotations

from typing import Self, Collection
from copy import deepcopy

from typing_extensions import Union


class ScriptBase:
    lines: list[str]

    def __init__(self) -> None:
        self.lines = []

    def append(self, commands: Union[str, Collection[str]]):
        if isinstance(commands, str):
            self.lines.append(commands + "\n")
        elif isinstance(commands, Collection):
            for x in commands:
                self.append(x)
        else:
            raise Exception(f"Invalid command type: {type(commands)}")

    def print(self):
        for line in self.lines:
            print(line, end="")

    def write(self, filename):
        if filename:
            f = open(filename, "w")
            f.writelines(self.lines)

    def copy(self) -> Self:
        """
        Creates a deep copy of the current ScriptBase instance.
        """
        return deepcopy(self)
