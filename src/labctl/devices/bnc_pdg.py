from __future__ import annotations
from typing_extensions import Union
from labctl.devices.base import DeviceBase


class BncPdgCmds(DeviceBase):
    @staticmethod
    def get_channel_number(channel: str) -> int:
        """
        Convert a channel name (A, B, C, D, E, F, G, H) to a number (1, 2, 3, 4, 5, 6, 7, 8)
        """
        if channel in "ABCDEFGH":
            return ord(channel) - ord("A") + 1
        else:
            raise ValueError(f"Invalid channel {channel}, should be in [A, B, ..., H]")

    @staticmethod
    def get_channel_name(channel: int) -> str:
        """
        Convert a channel number (1, 2, 3, 4, 5, 6, 7, 8) to a name (A, B, C, D, E, F, G, H)
        """
        if channel in range(1, 9):
            return chr(channel + ord("A") - 1)
        else:
            raise ValueError(f"Invalid channel {channel}, should be in [1, 2, ..., 8]")

    @staticmethod
    def verify_channel(channel: Union[str, int]) -> int:
        if isinstance(channel, str):
            return BncPdgCmds.get_channel_number(channel)
        elif isinstance(channel, int):
            if channel in range(1, 9):
                return channel
            else:
                raise ValueError(
                    f"Invalid channel {channel}, should be in [1, 2, ..., 8]"
                )

    def delay(self, channel, delay) -> BncPdgCmds:
        channel = self.verify_channel(channel)
        self.append(f":PULS{channel:d}:DELAY {delay:.10f}")
        return self

    def pulsewidth(self, channel, T_pulse) -> BncPdgCmds:
        channel = self.verify_channel(channel)
        self.append(f":PULS{channel:d}:WIDT {T_pulse:.10f}")
        return self

    def arm(self) -> BncPdgCmds:
        # Persist previous command by waiting for a bit
        self.parent.pause(50)

        self.append("*ARM")
        return self

    def burstcount(self, channel, count) -> BncPdgCmds:
        channel = self.verify_channel(channel)
        self.append(f":PULS{channel:d}:BCO {count:.0f}")
        return self

    def enable(self, channel, enable) -> BncPdgCmds:
        channel = self.verify_channel(channel)
        if enable:
            self.append(f":PULS{channel:d}:STAT ON")
        else:
            self.append(f":PULS{channel:d}:STAT OFF")
        return self

    def polarity(self, channel, polarity) -> BncPdgCmds:
        channel = self.verify_channel(channel)
        if polarity in ["NORM", "INV", "COMP"]:
            self.append(f":PULS{channel:d}:POL {polarity}")
        else:
            raise ValueError(
                f"Invalid polarity {polarity}, should be in [NORM, INV, COMP]"
            )
        return self

    def output(self, channel, mode, voltage=0) -> BncPdgCmds:
        channel = self.verify_channel(channel)
        if mode == "TTL":
            self.append(f":PULS{channel:d}:OUTP:MOD TTL")
        elif mode == "ADJ":
            self.append(f":PULS{channel:d}:OUTP:MOD ADJ")
            self.append(f":PULS{channel:d}:OUTP:AMPL {voltage:.1f}")
        return self

    def channel_mode(self, channel, mode) -> BncPdgCmds:
        channel = self.verify_channel(channel)
        if mode in ["NORM", "SING", "BURS", "DCYC"]:
            self.append(f":PULS{channel:d}:CMOD {mode}")
        else:
            raise ValueError(
                f"Invalid mode {mode}, should be in [NORM, SING, BURS, DCYC]"
            )
        return self

    def channel_gate(self, channel, gate) -> BncPdgCmds:
        channel = self.verify_channel(channel)
        if gate in ["DIS", "LOW", "HIGH"]:
            self.append(f":PULS{channel:d}:CGAT {gate}")
        else:
            raise ValueError(f"Invalid gate {gate}, should be in [DIS, LOW, HIGH]")
        return self

    def sync(self, channel, ref) -> BncPdgCmds:
        channel = self.verify_channel(channel)
        if ref == "T0":
            pass
        else:
            ref = "CH" + self.get_channel_name(ref)

        self.append(f":PULS{channel:d}:SYNC {ref}")
        return self
