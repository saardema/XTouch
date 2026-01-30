from collections.abc import Callable
import mido

from motu_xtouch.xtouch.mapping import XtouchMapping
from xtouch.control import ControlEventFlags, XTouchControlDescriptor


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

    def send_note_on(self, note: int, velocity: int, global_channel=False):
        channel = GLOBAL_CHANNEL if global_channel else 0
        msg = mido.Message('note_on', note=note, velocity=velocity, channel=channel)
        self._outport.send(msg)

    def set_cc_float(self, cc: int, value: float, global_channel=False):
        self.send_cc(cc, int(value * 127), global_channel)

    def send_cc(self, cc: int, value: int, global_channel=False):
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
