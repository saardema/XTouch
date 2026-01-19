from enum import Enum, auto
import mido


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

    def set_fader(self, i: int, value):
        self.set_cc(i + 1, value)

    def set_rotary(self, i: int, value, y: int = 0):
        self.set_cc(i + 10 + y * 8, value)

    def set_rotary_mode(self, i, mode: EncoderMode, y: int = 0):
        self.set_cc(i + 10 + y * 8, mode.value, 1)

    def set_cc(self, cc: int, value: int, channel=0):
        msg = mido.Message('control_change', control=cc, value=value, channel=channel)
        self.outport.send(msg)

    def set_button(self, x: int, y: int = 0, on=True, blink=False):
        velocity = 2 if blink else 1 if on else 0
        note = x + (y + 2) * 8
        msg = mido.Message('note_on', note=note, velocity=velocity)
        self.outport.send(msg)
