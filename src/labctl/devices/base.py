from labctl.script.base import ScriptBase


class DeviceBase:
    """
    Represents a collection of commands for a specific device.

    Attributes:
        parent (Cmds): The parent command collection.
    """

    parent: ScriptBase

    def __init__(self, parent: ScriptBase) -> None:
        self.parent = parent

    def append(self, commands) -> None:
        """
        Appends commands to the parent command collection.

        Args:
            commands: The commands to be appended.
        """
        self.parent.append(commands, device=self)
