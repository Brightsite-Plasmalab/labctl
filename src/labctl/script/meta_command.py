from labctl.script.base import ScriptBase
from typing_extensions import Self


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
        self.append(f"#WAIT {milliseconds:.0f}")
        self.total_wait += milliseconds
        return self

    def comment(self, comment) -> Self:
        """
        Add a comment to the script, which is printed in the terminal when the script is executed.
        """
        self.append(f"# {comment}")
        return self

    def test(self, test_command, result) -> Self:
        """
        Add a test command to the script, which is sent to a serial device and compared to the expected result.
        """
        self.append(f"#TEST {test_command} == {result}")
        return self
