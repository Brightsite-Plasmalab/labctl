from labctl.script.meta_command import MetaCommands
from labctl.script.upgrades import DeviceCommands, ScriptInfo


class Script(ScriptInfo, MetaCommands, DeviceCommands):
    pass
