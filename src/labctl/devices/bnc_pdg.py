from __future__ import annotations
from labctl.devices.impl import DeviceCmds


class BncPdgCmds(DeviceCmds):
    def __init__(self, parent):
        DeviceCmds.__init__(self, parent)

    def delay(self, channel, delay) -> BncPdgCmds:
        self.append(f":PULS{channel:d}:DELAY {delay:.10f}")
        return self

    def pulsewidth(self, channel, T_pulse) -> BncPdgCmds:
        self.append(f":PULS{channel:d}:WIDT {T_pulse:.10f}")
        return self

    def arm(self) -> BncPdgCmds:
        # Persist previous command by waiting for a bit
        self.parent.pause(50)

        self.append("*ARM")
        return self

    def burstcount(self, channel, count) -> BncPdgCmds:
        self.append(f":PULS{channel:d}:BCO {count:.0f}")
        return self
