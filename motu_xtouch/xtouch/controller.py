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

        self.controls_directory: dict[int, dict[int, dict[int, XTouchControl]]] = {}
        self.controls: dict[XTouchControlDescriptor, XTouchControl] = {}
        self.faders: list[Fader] = []
        self.buttons: list[Button] = []
        self.encoders: list[Encoder] = []

        self.init_controls()
        self.client.connect()

    def init_controls(self):
        for lookup in self.map.cc_lookup, self.map.note_lookup:
            for n, (descriptor, ranges) in lookup.items():
                if descriptor not in self.controls_directory:
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

    def on_control_event(self, descriptor: XTouchControlDescriptor, event: ControlEventFlags, midi_value: int):
        # ctrl_bin = f"{bin(descriptor.control_flags)[2:]:0>6}"
        # desc_bin = f"{bin(hash(descriptor))[2:]:0>13}"

        if not (ctrl := self.controls.get(descriptor)):
            return

        ctrl.handle_event(event, midi_value)
        self.callback(ctrl, event, ctrl.get_value())
        # print(self.controls.get(descriptor), descriptor.control_flags, event, value)
