from labctl.devices import ThorlabsRotationStageCmds
from labctl.script import Script

angle = 28.63 + 90.5

cmds = Script()
stage = ThorlabsRotationStageCmds(cmds)
cmds.register_device(stage, 1)
stage.goto_degrees(angle)
print(cmds.lines[-2])

# %%