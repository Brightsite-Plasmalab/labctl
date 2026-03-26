from __future__ import annotations
import time
from labctl.devices.base import DeviceBase
from labctl.script.base import ScriptBase


class ScriptInfo(ScriptBase):
    title: str | None
    date: str
    author: str | None

    def __init__(self, title: str | None = None, author: str | None = None) -> None:
        self.title = title
        self.date = time.strftime("%Y-%m-%d__%H:%M:%S")
        self.devices = {}
        self.author = author
        super().__init__()

    def header_info(self):
        self.append(f"# Configuration file for lab automation")
        if self.title is not None:
            self.append(f"#   Title:  {self.title}")
        self.append(f"#   Date:   {self.date}")
        if self.author is not None:
            self.append(f"#   Author: {self.author}")


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

    def append(self, commands: str | list[str], device=None):
        if device is not None:
            self.switch_device(device)

        super().append(commands)
