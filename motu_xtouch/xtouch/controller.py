from collections.abc import Callable

from motu_xtouch.core.core import Control, ControlEventFlags
from motu_xtouch.xtouch.control import Button, ControlFlags, Encoder, Fader, VolumeControl, XTouchControl
from xtouch.mapping import XTouchControlDescriptor, XtouchMapping
from xtouch.midi_client import XTouchMIDIClient


class XTouchController:

    def __init__(self, callback: Callable[[Control, ControlEventFlags, float], None]) -> None:
        self.map = XtouchMapping()
        self.client = XTouchMIDIClient(self.map, self.on_control_change)
        self.control_event_callback = callback

        self.controls_directory: dict[str, dict[int, dict[int, dict[int, XTouchControl]]]] = {}
        self.controls: dict[XTouchControlDescriptor, XTouchControl] = {}
        self.faders: list[Fader] = []
        self.buttons: list[Button] = []
        self.encoders: list[Encoder] = []

        self.client.connect()
        self.init_controls()

    def init_controls(self):
        for descriptor in self.map.descs.values():
            if descriptor.control_flags & ControlFlags.Fader:
                control = Fader(descriptor, self.client)
                self.faders.append(control)
                self.controls[descriptor] = control

            elif descriptor.control_flags & ControlFlags.Encoder:
                control = Encoder(descriptor, self.client)
                self.encoders.append(control)
                self.controls[descriptor] = control

            elif descriptor.control_flags & ControlFlags.Button:
                control = Button(descriptor, self.client)
                self.buttons.append(control)
                self.controls[descriptor] = control

    def on_parameter_change(self, control: XTouchControl, value):
        control.set_value(value)

    def on_control_change(self, descriptor: XTouchControlDescriptor, event: ControlEventFlags, midi_value: int):
        if not (ctrl := self.controls.get(descriptor)):
            return

        ctrl.handle_event(event, midi_value)
        self.control_event_callback(ctrl, event, ctrl.value)

    def set_encoder_mode(self, encoder: Encoder, mode: Encoder.Mode):
        encoder.mode = mode

        # When sending CC/Note to control the XTouch, the active
        # layer doesn't apply and instead it largely uses the
        # mapping of layer A, so retarget to layer A.
        if encoder.descriptor.layer == 1:
            encoder = self.encoders[self.encoders.index(encoder) % 16]
        encoder.set_mode(mode)

    # region Debug

    def debug(self, ctrl: XTouchControl, event: ControlEventFlags):
        desc = ctrl.descriptor
        location = desc.layer, desc.group, desc.i

        if isinstance(ctrl, Button):
            self.on_button_press(bool(event & ControlEventFlags.Down), location)

        elif isinstance(ctrl, Fader):
            moved = bool(event & ControlEventFlags.Move)
            touched = bool(event & ControlEventFlags.Down)
            self.on_fader_event(ctrl, ctrl.value, moved, touched, location)

        elif isinstance(ctrl, Encoder):
            moved = bool(event & ControlEventFlags.Move)
            pressed = bool(event & ControlEventFlags.Down)
            self.on_encoder_event(ctrl, ctrl.value, moved, pressed, location)

    @staticmethod
    def on_encoder_event(encoder: Encoder, value: float, moved: bool, pressed: bool, location: tuple[int, int, int]):
        if moved:
            print("Encoder move:", location, value)
        elif pressed:
            print("Encoder press:", location)

    @staticmethod
    def on_fader_event(fader: Fader, value: float, moved: bool, touched: bool, location: tuple[int, int, int]):
        if moved:
            print("Fader move:", fader.value, location)
        elif touched:
            print("Fader touch:", location)

    @staticmethod
    def on_button_press(pressed: bool, location: tuple[int, int, int]):
        if pressed:
            print("Button press:", location)
    # endregion Debug
