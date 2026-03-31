"""Compatibility helpers for building command scripts."""

from __future__ import annotations

import time
from labctl.devices.base import DeviceBase
from labctl.script.base import ScriptBase


class ScriptInfo(ScriptBase):
    """Script metadata helper for header comments."""

    title: str | None
    date: str
    author: str | None

    def __init__(self, title: str | None = None, author: str | None = None) -> None:
        """Initialize script metadata.

        Parameters
        ----------
        title : str | None, optional
            Optional script title.
        author : str | None, optional
            Optional author name.
        """
        self.title = title
        self.date = time.strftime("%Y-%m-%d__%H:%M:%S")
        self.devices = {}
        self.author = author
        super().__init__()

    def header_info(self) -> None:
        """Append script metadata comments to the command stream."""
        self.comment(f"Configuration file for lab automation")
        if self.title is not None:
            self.comment(f"  Title:  {self.title}")
        self.comment(f"  Date:   {self.date}")
        if self.author is not None:
            self.comment(f"  Author: {self.author}")


class DeviceCommands(ScriptBase):
    """Device/channel routing helper for script command emission."""

    current_channel: int = -1
    devices: dict[DeviceBase, int] = {}

    def register_device(self, device: DeviceBase, channel: int | None = None) -> int:
        """Register a device to a serial-switch channel.

        Parameters
        ----------
        device : DeviceBase
            Device command wrapper to register.
        channel : int | None, optional
            Channel number. If omitted, the first free channel is used.

        Returns
        -------
        int
            Assigned channel number.
        """
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

    def get_device_channel(self, device: DeviceBase) -> int:
        """Return the channel for a registered device.

        Parameters
        ----------
        device : DeviceBase
            Registered device.

        Returns
        -------
        int
            Channel number assigned to ``device``.
        """
        if device not in self.devices:
            raise Exception(f"Device {device} is not registered")
        return self.devices[device]

    def get_device_by_channel(self, channel: int) -> DeviceBase:
        """Return the device assigned to a channel.

        Parameters
        ----------
        channel : int
            Channel number.

        Returns
        -------
        DeviceBase
            Registered device for the channel.
        """
        for device, ch in self.devices.items():
            if ch == channel:
                return device
        raise Exception(f"No device registered on channel {channel}")

    def is_registered(self, device: DeviceBase) -> bool:
        """Check whether a device is registered.

        Parameters
        ----------
        device : DeviceBase
            Device to check.

        Returns
        -------
        bool
            ``True`` if the device is registered.
        """
        return device in self.devices

    def switch_device(self, channel: int | DeviceBase) -> None:
        """Switch active serial channel by channel id or device.

        Parameters
        ----------
        channel : int | DeviceBase
            Target channel id or registered device.
        """
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

    def append(
        self,
        commands: str | list[str],
        device: DeviceBase | None = None,
    ) -> None:
        """Append commands, optionally switching to a device first.

        Parameters
        ----------
        commands : str | list[str]
            Command string(s) to append.
        device : DeviceBase | None, optional
            Device to select before appending commands.
        """
        if device is not None:
            self.switch_device(device)

        super().append(commands)
