from collections.abc import Callable

from motu_xtouch.core.core import Control, ControlEventFlags
from motu_xtouch.xtouch.control import Button, ControlFlags, Encoder, Fader, XTouchControl
from xtouch.mapping import XTouchControlDescriptor, XtouchMapping
from xtouch.midi_client import XTouchMIDIClient


class XTouchController:
    def __init__(self, callback: Callable[[Control, ControlEventFlags, float], None]) -> None:
        self.map = XtouchMapping()
        self.client = XTouchMIDIClient(self.map, self.on_control_event)
        self.callback = callback

        self.controls_directory: dict[str, dict[int, dict[int, dict[int, XTouchControl]]]] = {}
        self.controls: dict[XTouchControlDescriptor, XTouchControl] = {}
        self.faders: list[Fader] = []
        self.buttons: list[Button] = []
        self.encoders: list[Encoder] = []

        self.client.connect()
        self.init_controls()

        for encoder in self.encoders:
            self.set_encoder_mode(encoder, encoder.mode)

    def init_controls(self):
        for lookup in self.map.cc_lookup, self.map.note_lookup:
            for n, (descriptor, ranges) in lookup.items():

                if descriptor in self.controls:
                    control = self.controls[descriptor]

                else:

                    if descriptor.control_flags & ControlFlags.Fader:
                        control = Fader(descriptor)
                        self.faders.append(control)
                        self.controls[descriptor] = control

                    elif descriptor.control_flags & ControlFlags.Encoder:
                        control = Encoder(descriptor)
                        self.encoders.append(control)
                        self.controls[descriptor] = control

                    elif descriptor.control_flags & ControlFlags.Button:
                        control = Button(descriptor)
                        self.buttons.append(control)
                        self.controls[descriptor] = control

                if lookup == self.map.cc_lookup:
                    control.ccs[descriptor.name] = n
                else:
                    control.notes[descriptor.name] = n

                desc = control.descriptor
                type_name = "fader" if control.is_fader else \
                    "encoder" if control.is_encoder else "button"
                type_dir = self.controls_directory.setdefault(type_name, {})
                layer_dir = type_dir.setdefault(desc.layer, {})
                group_dir = layer_dir.setdefault(desc.group, {})
                group_dir[desc.i] = control

    def on_control_event(self, descriptor: XTouchControlDescriptor, event: ControlEventFlags, midi_value: int):
        if not (ctrl := self.controls.get(descriptor)):
            return

        ctrl.handle_event(event, midi_value)
        self.callback(ctrl, event, ctrl.get_value())

        if descriptor.control_flags & ControlFlags.Button:
            self.on_button_event(
                descriptor.layer, descriptor.group, descriptor.i,
                event & ControlEventFlags.Down > 0
            )

    def on_button_event(self, layer, group, i, pressed):
        if pressed:
            print(layer, group, i)

    def set_encoder_mode(self, encoder: Encoder, mode: Encoder.Mode):
        encoder.mode = mode

        # When sending CC/Note to control the XTouch, the active
        # layer doesn't apply and instead it largely uses the
        # mapping of layer A, so retarget to layer A.
        g, i = encoder.descriptor.group, encoder.descriptor.i
        target = self.controls_directory["encoder"][0][g][i]
        self.client.set_cc(target.ccs["encoder"], mode.value, True)
