from __future__ import annotations
from typing_extensions import List, Union


class ScriptBase:
    lines: List[str] = []

    def __init__(self) -> None:
        self.lines = []

    def append(self, commands: Union[str, List[str]], device=None) -> ScriptBase:
        if type(commands) == str:
            self.lines.append(commands + "\n")
            return self
        elif type(commands) == list or type(commands) == tuple:
            for x in commands:
                self.append(x)
            return self
        else:
            raise Exception(f"Invalid command type: {type(commands)}")

    def __add__(self, other: Union[str, List[str]]) -> ScriptBase:
        self.append(other)
        return self

    def print(self):
        for line in self.lines:
            print(line, end="")
        return self

    def write(self, filename):
        if filename:
            f = open(filename, "w")
            f.writelines(self.lines)
        return self

    def copy(self, suffix="") -> ScriptBase:
        copy = self.new(suffix)
        copy.lines = self.lines
        return copy
