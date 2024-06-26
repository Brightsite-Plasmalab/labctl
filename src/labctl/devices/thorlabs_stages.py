from __future__ import annotations
from labctl.devices.base import DeviceBase


class ThorlabsStageCmds(DeviceBase):
    def home(self) -> ThorlabsStageCmds:
        # Home twice...
        for i in range(2):
            self.append("0ho0")
            self.parent.pause(2500)
        return self

    def forward(self) -> ThorlabsStageCmds:
        self.append("0fw")
        self.parent.pause(2500)
        return self

    def backward(self) -> ThorlabsStageCmds:
        self.append("0bw")
        self.parent.pause(2500)
        return self

    def goto(self, index) -> ThorlabsStageCmds:
        self.home()
        for _ in range(index):
            self.forward()
        return self
