from labctl.script.upgrades import DeviceCommands, ScriptInfo
from labctl.script.meta_command import MetaCommands


class Script(ScriptInfo, MetaCommands, DeviceCommands):
    pass
