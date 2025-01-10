from __future__ import annotations
from labctl.devices.base import DeviceBase

# Communications protocol: 'FSE-CCE PlasmaLab - General/manuals and quotes/Thorlabs/stages/Thorlabs_Rotation_mount_ELL14-Manual.pdf'


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


class ThorlabsRotationStageCmds(DeviceBase):
    PULSES_PER_REV = 143360  # 0x23000

    # See /Users/martijn/Projects/study/UM/Software/projects/hydrogen/rotation_stage.py
    def home(self) -> ThorlabsStageCmds:
        # Home twice...
        for _ in range(2):
            self.append("0ho0")
            self.parent.pause(1500)
        return self

    def goto(self, pulses) -> ThorlabsStageCmds:
        # self.home()  # Home first to ensure we know where we are

        self.append(f"0ma{self._pulse_string(pulses)}")
        pause_ms = pulses / self.PULSES_PER_REV * 1800 + 300

        self.parent.pause(pause_ms)

        return self

    def goto_degrees(self, degrees) -> ThorlabsStageCmds:
        pulses = int(degrees / 360 * self.PULSES_PER_REV) % self.PULSES_PER_REV
        self.goto(pulses)

    def _pulse_string(self, pulses):
        # Returns the pulses in an 8-length hexadecimal string
        return f"{pulses:08X}"
        # return f"{pulses:08x}"

    def move_relative(self, pulses=0, degrees=0) -> ThorlabsRotationStageCmds:
        if degrees != 0:
            pulses = int(degrees / 360 * self.PULSES_PER_REV) % self.PULSES_PER_REV
        elif pulses == 0:
            raise ValueError("Either pulses or degrees should be specified")

        self.append(f"0mr{self._pulse_string(pulses)}")
        self.parent.pause(pulses / self.PULSES_PER_REV * 1800 + 300)
