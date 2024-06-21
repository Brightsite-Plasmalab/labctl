from labctl.script.base import ScriptBase
from labctl.script.upgrades import DeviceCommands, MetaCommands, ScriptInfo


class Script(ScriptInfo, MetaCommands, DeviceCommands):
    pass
