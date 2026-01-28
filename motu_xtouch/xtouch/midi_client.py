from collections.abc import Callable
import mido

from motu_xtouch import float_to_midi
from motu_xtouch.xtouch.control import XTouchControl
from motu_xtouch.xtouch.mapping import ControlEventFlags, XTouchControlDescriptor, XtouchMapping


DEVICE_NAME = 'X-TOUCH COMPACT'


class XTouchMIDIClient:
    def __init__(
            self,
            map: XtouchMapping,
            callback: Callable[[XTouchControlDescriptor, ControlEventFlags, int], None]
    ) -> None:

        self.ready = False
        self.map = map
        self.callback = callback

    def connect(self):
        try:
            self._inport = mido.open_input(DEVICE_NAME, callback=self._on_midi_received)
            self._outport = mido.open_output(DEVICE_NAME)
            print('Connected to ' + DEVICE_NAME)
            self.ready = True

        except OSError as e:
            print(e)

    def set_control(self, control: XTouchControl, value):
        ...

    def _set_cc(self, cc: int, value: float, channel=0):
        value_int = float_to_midi(value)
        msg = mido.Message('control_change', control=cc, value=value_int, channel=channel)
        self._outport.send(msg)

    def _on_midi_received(self, msg: mido.Message):
        if msg.type not in ["note_on", "note_off", "control_change"]:
            return

        control_descriptor, event = self.map.digest_message(msg)

        if control_descriptor:
            value = msg.value if msg.is_cc() else msg.velocity
            self.callback(control_descriptor, event, value)
