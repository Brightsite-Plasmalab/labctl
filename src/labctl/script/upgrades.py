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
        self.comment(f"Configuration file for lab automation")
        if self.title is not None:
            self.comment(f"  Title:  {self.title}")
        self.comment(f"  Date:   {self.date}")
        if self.author is not None:
            self.comment(f"  Author: {self.author}")


class DeviceCommands(ScriptBase):
    current_channel: int = -1
    devices: dict[DeviceBase, int] = {}

    def register_device(self, device, channel=None):
        if channel is None:
            unoccupied_channels = set(range(1, 4)) - set(self.devices.values())
            if len(unoccupied_channels) == 0:
                raise Exception("No unoccupied channels available")
            channel = min(unoccupied_channels)

        if device in self.devices:
            raise Exception(
                f"Device {device} is already registered on channel {self.devices[device]}"
            )
        if channel in self.devices.values():
            raise Exception(
                f"Channel {channel} is already occupied by device {self.get_device_by_channel(channel)}"
            )

        print(f"Registering device {device} on channel {channel}")
        self.devices[device] = channel

        return channel

    def get_device_channel(self, device):
        if device not in self.devices:
            raise Exception(f"Device {device} is not registered")
        return self.devices[device]

    def get_device_by_channel(self, channel):
        for device, ch in self.devices.items():
            if ch == channel:
                return device
        raise Exception(f"No device registered on channel {channel}")

    def is_registered(self, device):
        return device in self.devices

    def switch_device(self, channel):
        if isinstance(channel, DeviceBase):
            self.switch_device(self.get_device_channel(channel))
        elif type(channel) == int:
            assert (
                self.get_device_by_channel(channel) is not None
            ), f"No device registered on channel {channel}"
            if self.current_channel != channel:
                self.append(f"#SELSER {channel}")
                self.current_channel = channel
        else:
            raise Exception(f"Invalid channel type: {type(channel)}")

    def append(self, commands: str | list[str], device=None):
        if device is not None:
            self.switch_device(device)

        super().append(commands)
