from enum import Enum
import mido

from motu_xtouch.mapping import BUTTONS, ENCODERS_CC


DEVICE_NAME = 'X-TOUCH COMPACT'


class EncoderMode(Enum):
    Single = 0
    Pan = 1
    Fan = 2
    Spread = 3
    Trim = 4


class XTouchClient:
    def __init__(self, callback=None) -> None:
        self.callback = callback
        self.ready = False

    def connect(self):
        try:
            self.inport = mido.open_input(DEVICE_NAME, callback=self.callback)
            self.outport = mido.open_output(DEVICE_NAME)
            print('Connected to ' + DEVICE_NAME)
            self.ready = True

        except OSError as e:
            print(e)

    def _set_cc(self, cc: int, value: int, channel=0):
        msg = mido.Message('control_change', control=cc, value=value, channel=channel)
        self.outport.send(msg)

    def _set_encoder(self, x: int, value: int, y: int = 0, ch: int = 0):
        if (cc := ENCODERS_CC.find(x % 8, y, x // 8)) is not None:
            self._set_cc(cc, value, ch)

    def set_fader(self, i: int, value):
        self._set_cc(i + 1, value)

    def set_encoder(self, x: int, value: int, y: int = 0):
        self._set_encoder(x, value, y)

    def set_encoder_mode(self, x, y: int = 0, mode: EncoderMode = EncoderMode.Fan):
        self._set_encoder(x, mode.value, y, 1)

    def set_button(self, x: int, y: int, mode: int):
        # Mode 0: off, 1: on, 2: blinking
        note = BUTTONS.find(x % 8, y, x // 8)
        if note is not None:
            msg = mido.Message('note_on', note=note, velocity=mode)
            self.outport.send(msg)
