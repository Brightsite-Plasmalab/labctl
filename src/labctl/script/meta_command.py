from labctl.script.base import ScriptBase

class MetaCommands(ScriptBase):
    """
    MetaCommands represents a collection of commands that are resolved by the interpreter rather than submitted over the serial port.
    Subclassing from MetaCommands allows for the use of the pause and comment methods.
    """

    total_wait = 0

    def pause(self, milliseconds):
        self.append(f"#WAIT {milliseconds:.0f}")
        self.total_wait += milliseconds

    def comment(self, comment):
        if not comment.startswith("# "):
            comment = "# " + comment
        self.append(comment)