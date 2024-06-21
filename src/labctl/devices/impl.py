from labctl.script.commands import Cmds
from labctl.devices.impl import DeviceBase


class DeviceCmds(DeviceBase):
    """
    Represents a collection of commands for a specific device.

    Attributes:
        parent (Cmds): The parent command collection.
    """

    parent: Cmds

    def __init__(self, parent: Cmds) -> None:
        self.parent = parent

    def append(self, commands) -> None:
        """
        Appends commands to the parent command collection.

        Args:
            commands: The commands to be appended.
        """
        self.parent.append(commands, device=self)
