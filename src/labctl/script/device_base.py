"""Base wrapper for device-specific command helpers."""

from labctl.script.meta_command import MetaCommands


class DeviceBase:
    """
    Represents a collection of commands for a specific device.

    Attributes:
        parent (Cmds): The parent command collection.
    """

    parent: MetaCommands

    def __init__(self, parent: MetaCommands) -> None:
        """Initialize with parent command collector.

        Parameters
        ----------
        parent : MetaCommands
            Parent script-like command collector.
        """
        self.parent = parent

    def append(self, commands: str | list[str]) -> None:
        """
        Appends commands to the parent command collection.

        Parameters
        ----------
        commands : str | list[str]
            Command(s) to append.
        """
        self.parent.append(commands, device=self)

    def __str__(self) -> str:
        """Return the device class name for logging and comments.

        Returns
        -------
        str
            Device class name.
        """
        return f"{self.__class__.__name__}"

    def preferred_baud_rate(self) -> int:
        """
        Returns the preferred baud rate for this device.

        Returns:
            int: The preferred baud rate.
        """
        return 115200

    def verify_device(self):
        """
        Verifies that the device is properly registered with the parent command collection.
        """
        if not self.parent.is_registered(self):
            raise Exception(
                f"Device {self} is not registered with the parent command collection"
            )
