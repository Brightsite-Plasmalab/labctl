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
