from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum, IntEnum, auto
import time
from typing import TYPE_CHECKING

from ctrl_mix.core.controller import Control

if TYPE_CHECKING:
    from ctrl_mix.xtouch.controller import XTouchController
    from ctrl_mix.xtouch.midi import XTouchMidiAdapter


class ControlType(IntEnum):
    Fader = auto()
    Encoder = auto()
    Button = auto()


class ControlSubType(IntEnum):
    Channel = auto()
    Main = auto()
    Side = auto()
    Transport = auto()


class XTouchControl(Control):
    def __init__(self, layer: int, index: int, controller: XTouchController):
        self.layer = layer
        self.index = index
        self.controller = controller
        self.adapter = controller.adapter

        ctrl_type = ControlType[self.__class__.__name__]
        self._id = ctrl_type << 6 | (index << 1) | layer
        self.value = 0.0
        self.is_pressed: bool = False
        self._is_enabled: bool = True

    @property
    def is_enabled(self):
        return self._is_enabled

    @is_enabled.setter
    def is_enabled(self, state: bool):
        if state:
            self._on_enabled()
        else:
            self._on_disabled()

    def _on_disabled(self): self._is_enabled = False
    def _on_enabled(self): self._is_enabled = True

    @abstractmethod
    def set_value(self, value: float, sync=True):
        """ Sets the value, updating the controller if sync==True"""

    @abstractmethod
    def sync(self):
        """ Updates the controller to reflect the current value """

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

    def __init__(self, layer: int, index: int, controller: XTouchController):
        super().__init__(layer, index, controller)

        self._mode: Encoder.Mode = Encoder.Mode.Fan
        self._t_press = 0.0
        self._dt_press = 0.0
        self._duration_press = 0.0

    def set_mode(self, mode: Mode, sync=True):
        """
        Changing mode can only be done globally, so if the
        active layer is different, it will update the wrong control
        """
        self._mode = mode
        if sync:
            self.adapter.set_encoder_mode(self.index, mode.value)

    def set_ring(self, value: float | None = None, blink=False):
        """
        Changing ring mode can only be done globally, so if the
        active layer is different, it will update the wrong control
        """
        self.adapter.set_encoder_ring(self.index, value, blink)

    def set_value(self, value: float, sync=True):
        self.value = value
        if sync:
            self.sync()

    def sync(self):
        self.adapter.set_encoder_value(self.layer, self.index, self.value)

    def _on_enabled(self):
        self._is_enabled = True
        self.set_mode(self._mode)

    def _on_disabled(self):
        self._is_enabled = False
        self.set_ring(0)

    def on_press(self):
        super().on_press()
        self._dt_press = time.time() - self._t_press
        self._t_press = time.time()

    def on_release(self):
        super().on_release()
        self._duration_press = time.time() - self._t_press


class Fader(XTouchControl):

    def set_value(self, value: float, sync=True):
        self.value = value
        if sync:
            self.sync()

    def sync(self):
        self.adapter.set_fader_value(self.layer, self.index, self.value)


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
    value: bool = False

    def set_value(self, value: bool, sync=True):
        self.value = bool(value)
        if sync:
            self.sync()

    def sync(self):
        self.set_led(self.value)

    def on_press(self):
        if self.is_toggle:
            self.value = not self.value

            if not self.value:
                # To ensure LED is off when toggled off,
                # set LED off when pressed to overwrite internal LED toggle
                self.set_led(False)

    def on_release(self):
        # The LED is always internally toggled off on release
        # So keep the LED on when value is toggled on
        if self.value:
            self.set_led(True)

    def set_led(self, state: bool):
        # self.adapter.set_button_state(self.layer, self.index, state)
        # if self.layer == 0:
        self.adapter.set_button_mode(self.index, state)
