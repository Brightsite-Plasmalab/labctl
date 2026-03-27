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
        """
        Pause the execution of the script for a certain number of milliseconds.
        """
        self += f"#WAIT {milliseconds:.0f}"
        self.total_wait += milliseconds
        return self

    def comment(self, comment) -> Self:
        """
        Add a comment to the script, which is printed in the terminal when the script is executed.
        """
        self += comment
        return self

    def test(self, test_command, result):
        """
        Add a test command to the script, which is sent to a serial device and compared to the expected result.
        """
        self += f"#TEST {test_command} == {result}"
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
                f"Channel {channel} is already occupied by device {self.get_device_by_channel(channel).__class__.__name__}"
            )

        print(f"Registering device {device.__class__.__name__} on channel {channel}")
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

    def append(self, commands: Union[str, List[str]], device=None) -> Self:
        if device is not None:
            self.switch_device(device)

        super().append(commands)
