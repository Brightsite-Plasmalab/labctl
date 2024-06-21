from __future__ import annotations
from labctl.devices.impl import DeviceCmds
from labctl.script.commands import Cmds


class PiTranslationStage(DeviceCmds):
    x_current: float

    def __init__(self, parent):
        DeviceCmds.__init__(self, parent)

    def stop(self) -> PiTranslationStage:
        """Stop motion of all axes immediately"""
        self.append("STP")
        return self

    def SAI(self) -> PiTranslationStage:
        """Identify axis names"""
        self.append("SAI")
        return self

    def reset_error(self) -> PiTranslationStage:
        """Reset errors"""
        self.append("ERR?")
        return self

    def set_reference_mode(self, axis=1, mode="manual") -> PiTranslationStage:
        """Set the reference mode of the specified axis to manual or reference move"""
        modenum = 0 if mode == "manual" else 1
        if modenum == 1:
            raise NotImplementedError("Reference move mode not implemented yet")

        self.append(f"RON {axis:d} {modenum:d}")
        return self

    def set_servo(self, axis=1, enable=True) -> PiTranslationStage:
        """Enable or disable the servo of the specified axis"""
        self.append(f"SVO {axis:d} {int(enable):d}")
        return self

    def set_position(self, axis=1, position=0.0) -> PiTranslationStage:
        """Set the position of the specified axis"""
        self.append(f"POS {axis:d} {position:.3f}")
        self.x_current = position
        return self

    def get_position(self) -> PiTranslationStage:
        """Get the current position of the specified axis"""
        self.append("POS?")
        return self

    def move_to(self, axis=1, position=0.0) -> PiTranslationStage:
        """Move the specified axis to the specified position"""
        self.append(f"MOV {axis:d} {position:.3f}")
        dx = abs(position - self.x_current)
        T_wait = dx * 2
        self.parent.pause(T_wait * 1000)
        self.x_current = position
        return self

    def get_last_move(self) -> PiTranslationStage:
        """Get the last movement command"""
        self.append("MOV?")
        return self


if __name__ == "__main__":
    cmds = Cmds()
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
