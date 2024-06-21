from __future__ import annotations
from ast import Not
from typing import List, Union
import time
from labctl.devices.base import DeviceBase


class Cmds:
    total_wait = 0

    title: str | None = None
    date: str | None = None
    author: str | None = None

    lines: List[str] = []

    current_channel: int = 0
    devices: dict[DeviceBase, int] = {}

    def __init__(self, title: str | None = None, author: str | None = None) -> None:
        self.title = title
        self.date = time.strftime("%Y-%m-%d__%H:%M:%S")
        self.devices = {}
        self.author = author
        self.lines = []

    def register_device(self, device, channel):
        self.devices[device] = channel

    def is_registered(self, device):
        return device in self.devices

    def switch_device(self, channel):
        if isinstance(channel, DeviceBase):
            self.switch_device(self.devices[channel])
        elif type(channel) == int:
            if self.current_channel != channel:
                self.append(f"#SELSER {channel}")
                self.current_channel = channel
        else:
            raise Exception(f"Invalid channel type: {type(channel)}")

    def append(self, commands: Union[str, List[str]], device=None) -> Cmds:
        if device is not None:
            self.switch_device(device)

        if type(commands) == str:
            self.lines.append(commands + "\n")
            return self
        elif type(commands) == list or type(commands) == tuple:
            for x in commands:
                self.append(x)
            return self
        else:
            raise Exception(f"Invalid command type: {type(commands)}")

    def __add__(self, other: Union[str, List[str]]) -> Cmds:
        self.append(other)
        return self

    def header_info(self) -> Cmds:
        self += f"# Configuration file for lab automation"
        if self.title is not None:
            self += f"#   Title:  {self.title}"
        self += f"#   Date:   {self.date}"
        self += f"#   Author: {self.author}"
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

    def new(self, suffix="") -> Cmds:
        copy = Cmds((self.title if self.title else "") + suffix, self.author)
        copy.date = self.date
        return copy

    def copy(self, suffix="") -> Cmds:
        copy = self.new(suffix)
        copy.lines = self.lines
        return copy

    def pause(self, milliseconds) -> Cmds:
        self += f"#WAIT {milliseconds:.0f}"
        self.total_wait += milliseconds
        return self

    def comment(self, comment) -> Cmds:
        self += comment
        return self
