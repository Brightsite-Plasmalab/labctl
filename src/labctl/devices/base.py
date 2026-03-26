from labctl.script.meta_command import MetaCommands


class DeviceBase:
    """
    Represents a collection of commands for a specific device.

    Attributes:
        parent (Cmds): The parent command collection.
    """
    parent: MetaCommands

    def __init__(self, parent: MetaCommands) -> None:
        self.parent = parent

    def append(self, commands) -> None:
        """
        Appends commands to the parent command collection.

        Args:
            commands: The commands to be appended.
        """
        self.parent.append(commands, device=self)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}"
