from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, IntFlag, auto

from motu_xtouch.core.core import Control, ControlDescriptor, ControlEventFlags


class ControlFlags(IntFlag):
    Invalid = 0
    Fader = auto()
    Encoder = auto()
    Button = auto()
    Transport = auto()
    Master = auto()

    def __repr__(self) -> str:
        return self.name or self.__name__


@dataclass(frozen=True)
class XTouchControlDescriptor(ControlDescriptor):
    layer: int
    group: int
    i: int
    control_flags: ControlFlags

    def __hash__(self) -> int:
        h = self.control_flags
        h = h << 1 | self.layer
        h = h << 2 | self.group
        h = h << 3 | self.i

        return h


@dataclass
class XTouchControl(Control, ABC):
    descriptor: XTouchControlDescriptor

    def __post_init__(self):
        self.is_fader = bool(self.descriptor.control_flags & ControlFlags.Fader)
        self.is_encoder = bool(self.descriptor.control_flags & ControlFlags.Encoder)
        self.is_button = bool(self.descriptor.control_flags & ControlFlags.Button)

    @abstractmethod
    def handle_event(self, event_flags: ControlEventFlags, value: int): ...

    def __hash__(self) -> int:
        return hash(self.descriptor)

    @abstractmethod
    def get_value(self) -> float: ...


@dataclass(eq=False)
class Encoder(XTouchControl):
    class Mode(Enum):
        """
        CC values to send on global channel
        to change the visualization of the value
        """
        Single = 0
        Pan = 1
        Fan = 2
        Spread = 3
        Trim = 4

    value: float = 0
    pressed: bool = False
    mode: Mode = Mode.Fan

    def get_value(self) -> float:
        return self.value

    def handle_event(self, event_flags: ControlEventFlags, value: int):
        if event_flags & ControlEventFlags.Move:
            self.value = value / 127

        elif event_flags & ControlEventFlags.Press:
            self.pressed = value > 0


@dataclass(eq=False)
class Fader(XTouchControl):
    value: float = 0
    touched: bool = False

    def get_value(self) -> float:
        return self.value

    def handle_event(self, event_flags: ControlEventFlags, value: int):
        if event_flags & ControlEventFlags.Move:
            self.value = value / 127

        elif event_flags & ControlEventFlags.Press:
            self.touched = value > 0


@dataclass(eq=False)
class Button(XTouchControl):
    class Mode(Enum):
        """
        Note on velocity to send on global channel
        to control the LED state
        """
        Off = 0
        On = 1
        Blink = 2

    pressed: bool = False
    mode: Mode = Mode.Off

    def get_value(self) -> float:
        return float(self.pressed)

    def handle_event(self, event_flags: ControlEventFlags, value: int): ...
