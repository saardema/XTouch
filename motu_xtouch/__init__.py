from dataclasses import dataclass, field
from enum import Enum, Flag, auto
import math


type T_Store = int | float | str


def midi_to_float(value: int, db=True):
    if db:
        gain = value / 100
        exp = -8 + gain * 8
        f = 2 ** exp
        f -= 2 ** -8
    else:
        f = value / 127

    return min(max(f, 0), 4)


def float_to_midi(value, db=True):
    if value <= 0:
        return 0

    if db:
        value += 2 ** -8
        exp = math.log2(value)
        gain = 1 - exp / -8
        value = gain * 100
    else:
        value *= 127

    value = int(min(max(value, 0), 127))

    return value


class ChannelType(Enum):
    Disabled = 0
    Input = auto()
    Group = auto()
    Aux = auto()
    Master = auto()


class ControlType(Flag):
    Invalid = 0
    Fader = auto()
    Rotary = auto()
    Button = auto()
    Press = auto()
    Release = auto()
    CC = auto()
    Transport = auto()

    def __repr__(self) -> str:
        return self.name or self.__name__


@dataclass(repr=True)
class MixerChannel:
    name: str
    base_name: str = ""
    is_stereo: bool = False
    is_right_channel: bool = False
    bank_idx: int = -1
    bank_ch_idx: int = -1
    mix_in_idx: int = -1
    x_touch_idx: int = -1

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.base_name} [{self.mix_in_idx}, {self.bank_idx}, {self.bank_ch_idx}])"

    def __post_init__(self):
        self.base_name = self.name

        if self.name.endswith(" L"):
            self.base_name = self.name.removesuffix(" L")
            self.is_stereo = True
        elif self.name.endswith(" R"):
            self.base_name = self.name.removesuffix(" R")
            self.is_stereo = True
            self.is_right_channel = True


@dataclass
class InputBank:
    idx: int
    name: str = ""
    channel_type: ChannelType = ChannelType.Input
    n_channels: int = 0
    channels: dict[int, MixerChannel] = field(default_factory=lambda: {})
