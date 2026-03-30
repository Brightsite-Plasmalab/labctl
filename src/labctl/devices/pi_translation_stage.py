from __future__ import annotations
from labctl.devices.base import DeviceBase
from labctl.script.base import ScriptBase


class PiTranslationStage(DeviceBase):
    x_current: float

    def verify_device(self):
        super().verify_device()
        self.parent.test(
            self, "*IDN?", "(c)2018 Physik Instrumente", allow_overflow=True
        )

    def preferred_baud_rate(self):
        return 115200

    def stop(self):
        """Stop the motion of all axes immediately"""
        self.append("STP")

    def SAI(self):
        """Identify axis names"""
        self.append("SAI")

    def reset_error(self):
        """Reset errors"""
        self.append("ERR?")

    def set_reference_mode(self, axis=1, mode="manual"):
        """Set the reference mode of the specified axis to manual or reference move"""
        modenum = 0 if mode == "manual" else 1
        if modenum == 1:
            raise NotImplementedError("Reference move mode not implemented yet")

        self.append(f"RON {axis:d} {modenum:d}")

    def set_servo(self, axis=1, enable=True):
        """Enable or disable the servo of the specified axis"""
        self.append(f"SVO {axis:d} {int(enable):d}")

    def set_position(self, axis=1, position=0.0):
        """Set the position of the specified axis"""
        self.append(f"POS {axis:d} {position:.3f}")
        self.x_current = position

    def get_position(self):
        """Get the current position of the specified axis"""
        self.append("POS?")

    def move_to(self, axis=1, position=0.0):
        """Move the specified axis to the specified position"""
        self.append(f"MOV {axis:d} {position:.3f}")
        dx = abs(position - self.x_current)
        T_wait = dx * 2
        self.parent.pause(T_wait * 1000)
        self.x_current = position

    def get_last_move(self):
        """Get the last movement command"""
        self.append("MOV?")


if __name__ == "__main__":
    cmds = ScriptBase()
    translation_stage = PiTranslationStage(cmds)
    cmds.register_device(translation_stage, 1)
    translation_stage.stop()
    translation_stage.SAI()
    translation_stage.reset_error()
    translation_stage.set_reference_mode()
    translation_stage.set_servo(axis=1, enable=True)
    translation_stage.set_position(axis=1, position=0.0)
    translation_stage.get_position()
    translation_stage.move_to(axis=1, position=1.0)
    translation_stage.get_last_move()

    translation_stage.parent.print()
