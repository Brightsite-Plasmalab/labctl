from __future__ import annotations
from typing_extensions import List, Self, Union
import time
from labctl.devices.base import DeviceBase
from labctl.script.base import ScriptBase


class MetaCommands(ScriptBase):
    """
    MetaCommands represents a collection of commands that are resolved by the interpreter rather than submitted over the serial port.
    Subclassing from MetaCommands allows for the use of the pause and comment methods.
    """

    total_wait = 0

    def pause(self, milliseconds) -> Self:
        self += f"#WAIT {milliseconds:.0f}"
        self.total_wait += milliseconds
        return self

    def comment(self, comment) -> Self:
        self += comment
        return self


class ScriptInfo(ScriptBase):
    title: str | None = None
    date: str | None = None
    author: str | None = None

    def __init__(self, title: str | None = None, author: str | None = None) -> None:
        self.title = title
        self.date = time.strftime("%Y-%m-%d__%H:%M:%S")
        self.devices = {}
        self.author = author
        self.lines = []

    def header_info(self) -> Self:
        self += f"# Configuration file for lab automation"
        if self.title is not None:
            self += f"#   Title:  {self.title}"
        self += f"#   Date:   {self.date}"
        self += f"#   Author: {self.author}"
        return self


class DeviceCommands(ScriptBase):
    current_channel: int = -1
    devices: dict[DeviceBase, int] = {}

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

    def append(self, commands: Union[str, List[str]], device=None) -> Self:
        if device is not None:
            self.switch_device(device)

        super().append(commands)
