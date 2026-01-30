from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, IntFlag, auto
from typing import TYPE_CHECKING, Any, Any

from motu_xtouch import gain_to_norm, norm_to_gain
from motu_xtouch.core.core import Control, ControlDescriptor, ControlEventFlags

if TYPE_CHECKING:
    from motu_xtouch.xtouch.midi_client import XTouchMIDIClient


class ControlFlags(IntFlag):
    Invalid = 0
    Fader = auto()
    Encoder = auto()
    Button = auto()
    Transport = auto()
    Master = auto()

    BaseMask = Fader | Encoder | Button

    def __repr__(self) -> str:
        return self.name or self.__name__


@dataclass(eq=False)
class XTouchControlDescriptor(ControlDescriptor):
    layer: int
    group: int
    i: int
    control_flags: ControlFlags

    move: int = -1
    press: int = -1

    def __hash__(self) -> int:
        h = self.control_flags
        h = h << 1 | self.layer
        h = h << 2 | self.group
        h = h << 3 | self.i

        return h


class XTouchControl(Control):
    def __init__(self, descriptor: XTouchControlDescriptor, client: XTouchMIDIClient):
        self.descriptor: XTouchControlDescriptor = descriptor
        self.client: XTouchMIDIClient = client

        self.is_fader = bool(descriptor.control_flags & ControlFlags.Fader)
        self.is_encoder = bool(descriptor.control_flags & ControlFlags.Encoder)
        self.is_button = bool(descriptor.control_flags & ControlFlags.Button)

    @abstractmethod
    def handle_event(self, event_flags: ControlEventFlags, value: int): ...

    def __hash__(self) -> int:
        return hash(self.descriptor)

    def set_value(self, val): ...


class VolumeControl(XTouchControl, ABC):
    midi_value: int = 0
    touched: bool = False

    @property
    def normalized(self):
        return self.midi_value / 127

    @property
    def gain(self):
        return norm_to_gain(self.normalized)

    @property
    def value(self) -> float:
        return self.gain

    def set_value(self, val, is_gain=True):
        if is_gain:
            val = gain_to_norm(val)

        self.midi_value = int(val * 127)
        self.client.send_cc(self.descriptor.move, self.midi_value)

    def handle_event(self, event_flags: ControlEventFlags, midi_value: int):
        if event_flags & ControlEventFlags.Move:
            self.midi_value = midi_value

        elif event_flags & ControlEventFlags.Press:
            self.touched = midi_value > 0


class Encoder(VolumeControl, XTouchControl):
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

    # pressed: bool = False
    mode: Mode = Mode.Fan

    def set_mode(self, mode: Mode):
        self.mode = mode
        self.client.send_cc(self.descriptor.move, mode.value, True)


class Fader(VolumeControl, XTouchControl):
    ...


class Button(XTouchControl):
    class LEDMode(Enum):
        """
        Note on velocity to send on global channel
        to control the LED state
        """
        Off = 1
        On = 2
        Blink = 3

    led_mode: LEDMode = LEDMode.Off
    is_toggle: bool = False
    toggled: bool = False

    @property
    def value(self) -> int:
        if self.is_toggle:
            return int(self.toggled)

        return int(self.pressed)

    def set_value(self, value: Any):
        state = bool(value)

        if self.is_toggle:
            self.toggled = state

        self.set_led(self.LEDMode.On if state else self.LEDMode.Off)

    def handle_event(self, event_flags: ControlEventFlags, value: int):
        self.pressed = value > 0

        if self.pressed:
            if self.is_toggle:
                self.set_value(not self.toggled)

        elif self.led_mode != self.LEDMode.Off:
            self.set_led(self.led_mode)

    def set_led(self, state: LEDMode):
        self.led_mode = state
        self.client.send_note_on(self.descriptor.press - 16, state.value, True)
