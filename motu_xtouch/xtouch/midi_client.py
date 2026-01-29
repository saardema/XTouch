from collections.abc import Callable
import mido

from motu_xtouch import float_to_midi
from motu_xtouch.xtouch.mapping import ControlEventFlags, XTouchControlDescriptor, XtouchMapping


DEVICE_NAME = 'X-TOUCH COMPACT'
GLOBAL_CHANNEL = 1


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

    def set_cc_float(self, cc: int, value: float, log_to_lin=True, global_channel=False):
        value = float_to_midi(value, log_to_lin)
        self.set_cc(cc, value, global_channel)

    def set_cc(self, cc: int, value: int, global_channel=False):
        channel = GLOBAL_CHANNEL if global_channel else 0
        msg = mido.Message('control_change', control=cc, value=value, channel=channel)
        self._outport.send(msg)

    def _on_midi_received(self, msg: mido.Message):
        if msg.type not in ["note_on", "note_off", "control_change"]:
            return

        descriptor, event = self.map.digest_message(msg)

        if descriptor:
            value = msg.value if msg.is_cc() else msg.velocity
            self.callback(descriptor, event, value)
