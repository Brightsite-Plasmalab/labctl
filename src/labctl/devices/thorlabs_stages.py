"""Command helpers for Thorlabs linear and rotation stages."""

from __future__ import annotations

from labctl.devices.base import DeviceBase

# Communications protocol: 'FSE-CCE PlasmaLab - General/manuals and quotes/Thorlabs/stages/Thorlabs_Rotation_mount_ELL14-Manual.pdf'


class ThorlabsStageCmds(DeviceBase):
    """Low-level command wrapper for Thorlabs filter/linear stages."""

    def verify_device(self):
        super().verify_device()
        self.parent.test(self, "0in", "0IN0E114", allow_overflow=True)

    def preferred_baud_rate(self):
        return 9600

    def home(self):
        """Home the stage position (issued twice for reliability)."""

        # Home twice...
        for i in range(2):
            self.append("0ho0")
            self.parent.pause(2500)

    def forward(self) -> None:
        """Jog the stage one step forward."""
        self.append("0fw")
        self.parent.pause(2500)

    def backward(self) -> None:
        """Jog the stage one step backward."""
        self.append("0bw")
        self.parent.pause(2500)

    def goto(self, index: int) -> None:
        """Move to an index by homing then stepping forward.

        Parameters
        ----------
        index : int
            Target step index from home.
        """
        self.home()
        for _ in range(index):
            self.forward()


class ThorlabsRotationStageCmds(DeviceBase):
    """Low-level command wrapper for Thorlabs rotation stages."""

    PULSES_PER_REV = 143360  # 0x23000

    def verify_device(self):
        super().verify_device()
        self.parent.test(self, "0in", "0IN0E114", allow_overflow=True)

    def preferred_baud_rate(self):
        return 9600

    # See /Users/martijn/Projects/study/UM/Software/projects/hydrogen/rotation_stage.py
    def home(self) -> None:
        """Home the rotation stage (issued twice for reliability)."""
        # Home twice...
        for _ in range(2):
            self.append("0ho0")
            self.parent.pause(1500)

    def goto(self, pulses: int) -> None:
        """Move the rotation stage to an absolute pulse position.

        Parameters
        ----------
        pulses : int
            Absolute pulse position in one revolution.
        """
        # self.home()  # Home first to ensure we know where we are
        self.append(f"0ma{self._pulse_string(pulses)}")
        pause_ms = pulses / self.PULSES_PER_REV * 1800 + 300

        self.parent.pause(pause_ms)

    def goto_degrees(self, degrees: float) -> None:
        """Move the stage to an angle in degrees.

        Parameters
        ----------
        degrees : float
            Target angle in degrees.
        """
        pulses = int(degrees / 360 * self.PULSES_PER_REV) % self.PULSES_PER_REV
        self.goto(pulses)

    def _pulse_string(self, pulses: int) -> str:
        """Format pulse position as an 8-character uppercase hex string.

        Parameters
        ----------
        pulses : int
            Pulse count value.

        Returns
        -------
        str
            Pulse value formatted for the controller protocol.
        """
        # Returns the pulses in an 8-length hexadecimal string
        return f"{pulses:08X}"

    def move_relative(self, pulses: int = 0, degrees: float = 0) -> None:
        """Move the stage relative to current position.

        Parameters
        ----------
        pulses : int, optional
            Relative pulse movement.
        degrees : float, optional
            Relative angle movement in degrees.

        Raises
        ------
        ValueError
            If both ``pulses`` and ``degrees`` are zero.
        """
        if degrees != 0:
            pulses = int(degrees / 360 * self.PULSES_PER_REV) % self.PULSES_PER_REV
        elif pulses == 0:
            raise ValueError("Either pulses or degrees should be specified")

        self.append(f"0mr{self._pulse_string(pulses)}")
        self.parent.pause(pulses / self.PULSES_PER_REV * 1800 + 300)
