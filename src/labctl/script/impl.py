"""Concrete script class composing metadata, meta commands, and device routing."""

from labctl.script.meta_command import MetaCommands
from labctl.script.upgrades import DeviceCommands, ScriptInfo


class Script(ScriptInfo, MetaCommands, DeviceCommands):
    """Concrete script object used across experiments."""

    pass
