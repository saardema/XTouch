from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum, IntEnum, auto
from typing import TYPE_CHECKING

from ctrl_mix.core.controller import Control

if TYPE_CHECKING:
    from ctrl_mix.xtouch.midi import XTouchMidiAdapter


class ControlType(IntEnum):
    Fader = auto()
    Encoder = auto()
    Button = auto()

    Channel = auto()
    Main = auto()
    Side = auto()
    Transport = auto()


class XTouchControl(Control):
    def __init__(self, layer: int, index: int, adapter: XTouchMidiAdapter):
        self.layer = layer
        self.index = index
        self.adapter = adapter

        ctrl_type = ControlType[self.__class__.__name__]
        self._id = ctrl_type << 6 | (index << 1) | layer
        self.value: float = 0.0
        self.is_pressed: bool = False

    @abstractmethod
    def set_value(self, value: float):
        """ Sets the value and updates the controller.
            For state and events coming from outside the controller.
        """

    @abstractmethod
    def sync_value(self, value: float):
        """ Sets the value without updating the controller.
            For events coming from the controller.
        """

    def on_press(self):
        self.is_pressed = True

    def on_release(self):
        self.is_pressed = False

    def __hash__(self) -> int:
        return self._id


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

    _mode: Mode = Mode.Fan

    def set_mode(self, mode: Mode):
        """
        Changing mode can only be done globally, so if the
        active layer is different, it will update the wrong control
        """
        self._mode = mode
        self.adapter.set_encoder_mode(self.index, mode.value)

    def set_ring(self, value, blink=False, single=True):
        """
        Changing ring mode can only be done globally, so if the
        active layer is different, it will update the wrong control
        """
        self.adapter.set_encoder_ring(self.index, value, blink, single)

    def set_value(self, value: float):
        self.sync_value(value)
        self.adapter.set_encoder_value(self.layer, self.index, value)

    def sync_value(self, value: float):
        self.value = value


class Fader(XTouchControl):

    def set_value(self, value: float):
        self.sync_value(value)
        self.adapter.set_fader_value(self.layer, self.index, value)

    def sync_value(self, value: float):
        self.value = value


class Button(XTouchControl):
    class LEDMode(Enum):
        """
        Note on velocity to send on global channel to control the LED state.
        State is stored per control, but MIDI is dispatched by the controller,
        because the CC mapping is global, not tied to layers.
        """
        Off = 0
        On = 2
        Blink = 3

    is_toggle: bool = False
    _led_mode: LEDMode = LEDMode.Off
    state: bool = False

    def set_state(self, state: bool):
        self.set_value(1.0 if state else 0.0)

    def set_value(self, value: float):
        self.sync_value(value)
        self.set_led(self.state)

    def sync_value(self, value: float):
        self.state = value > 0.5
        self.value = float(self.state)

    def on_press(self):
        if self.is_toggle:
            new_value = 1.0

            if self.state:
                new_value = 0.0

                # To ensure LED is off when toggled off,
                # set LED off when pressed to overwrite internal LED toggle
                self.set_led(False)

            self.sync_value(new_value)

    def on_release(self):
        # The LED is always internally toggled off on release
        # So keep the LED on when state is toggled on
        if self.state:
            self.set_led(True)

    def set_led(self, state: bool):
        # self.adapter.set_button_state(self.layer, self.index, state)
        # if self.layer == 0:
        self.adapter.set_button_mode(self.index, state)
