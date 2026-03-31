"""Meta command extensions for script control flow and comments."""

from labctl.script.base import ScriptBase
from typing_extensions import Self


class MetaCommands(ScriptBase):
    """
    MetaCommands represents a collection of commands that are resolved by the interpreter rather than submitted over the serial port.
    Subclassing from MetaCommands allows for the use of the pause and comment methods.
    """

    total_wait = 0

    def pause(self, milliseconds: float) -> Self:
        """
        Pause the execution of the script for a certain number of milliseconds.

        Parameters
        ----------
        milliseconds : float
            Wait time in milliseconds.

        Returns
        -------
        Self
            Current instance for method chaining.
        """
        self.append(f"#WAIT {milliseconds:.0f}")
        self.total_wait += milliseconds
        return self

    def comment(self, comment: str) -> Self:
        """
        Add a comment to the script, which is printed in the terminal when the script is executed.

        Parameters
        ----------
        comment : str
            Comment text.

        Returns
        -------
        Self
            Current instance for method chaining.
        """
        if not comment.startswith("# "):
            comment = "# " + comment
        self.append(f"# {comment}")
        return self

    def test(self, test_command: str, result: str) -> Self:
        """
        Add a test command to the script, which is sent to a serial device and compared to the expected result.

        Parameters
        ----------
        test_command : str
            Command to execute.
        result : str
            Expected device response.

        Returns
        -------
        Self
            Current instance for method chaining.
        """
        self.append(f"#TEST {test_command} == {result}")
        return self
