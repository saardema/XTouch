from __future__ import annotations
from collections.abc import Callable
from enum import Flag, auto
import mido

from ctrl_mix.xtouch.control import ControlType


DEVICE_NAME = "X-TOUCH COMPACT"


class XTouchMIDIClient:

    def __init__(
            self,
            midi_callback: Callable,
    ) -> None:

        self.ready = False
        self.midi_callback = midi_callback

    def connect(self):
        try:
            self._inport = mido.open_input(DEVICE_NAME, callback=self._on_midi_received)
            self._outport = mido.open_output(DEVICE_NAME)
            print('Connected to ' + DEVICE_NAME)
            self.ready = True

        except OSError as e:
            print(e)

    def send_note_on(self, note: int, velocity: int, channel: int):
        msg = mido.Message('note_on', note=note, velocity=velocity, channel=channel)
        self._outport.send(msg)

    def send_cc(self, cc: int, value: int, channel: int):
        msg = mido.Message('control_change', control=cc, value=value, channel=channel)
        self._outport.send(msg)

    def _on_midi_received(self, msg: mido.Message):
        if msg.type not in ["note_on", "note_off", "control_change"]:
            return

        num = msg.control if msg.is_cc() else msg.note
        value = msg.value if msg.is_cc() else msg.velocity
        self.midi_callback(msg.is_cc(), msg.channel, num, value)


"""
=====================  Mapping  =====================
Control        |   Channel | Main/Extra | Transport |
---------------|-----------|------------|-----------|
Button         |           |            |           |
  Press (note) |   0 -  31 |         32 |   33 - 39 |
Fader          |           |            |           |
  Move  (CC)   |   0 -   7 |          8 |           |
  Touch (CC)   | 100 - 107 |        108 |           |
Encoder        |           |            |           |
  Press (note) |  55 -  62 |    63 - 70 |           |
  Move  (CC)   |  10 -  17 |    18 - 25 |           |

Layer A => CH 1
Layer B => CH 2
"""


class CtrlEvent(Flag):
    Move = auto()
    Press = auto()
    Start = auto()
    End = auto()

    Pressed = Press | Start
    Released = Press | End


class XTouchMidiAdapter:

    cc_map = [
        (ControlType.Fader, CtrlEvent.Move, range(9), "main", {"channel": 7}),
        (ControlType.Encoder, CtrlEvent.Move, range(10, 26), "side", {"channel": 17}),
        (ControlType.Fader, CtrlEvent.Press, range(100, 110), "main", {"channel": 107}),
    ]

    note_map = [
        (ControlType.Button, CtrlEvent.Press, range(55), "transport", {"channel": 31, "main": 32}),
        (ControlType.Encoder, CtrlEvent.Press, range(55, 71), "side", {"channel": 62}),
    ]

    global_channel: int = 2
    encoder_cc_start: int = cc_map[1][2].start

    def __init__(
            self,
            value_change_callback: Callable[[ControlType, CtrlEvent, int, int, float], None]) -> None:

        self.client = XTouchMIDIClient(self.on_control_changed)
        self.ctrl_change_callback = value_change_callback
        self.client.connect()

    def on_control_changed(self, is_cc: bool, layer: int, number: int, value: int):
        normalized = value / 127
        idx = number

        lookup = self.cc_map if is_cc else self.note_map
        for ctrl, event, sequence, default, sub_types in lookup:
            if number in sequence:
                idx = number - sequence.start
                sub_type = default
                for st, div in sub_types.items():
                    if number <= div:
                        sub_type = st
                        break
                break
        else:
            print(f"Unhandled CC: chan {layer}, CC {number}, value {value}")
            return

        if event & CtrlEvent.Press:
            if value > 0:
                event |= CtrlEvent.Start
            else:
                event |= CtrlEvent.End

        # print(event, sub_type, ctrl.name.lower(), idx)

        self.ctrl_change_callback(ctrl, event, layer, idx, normalized)

    def set_fader_value(self, layer: int, index: int, value: float):
        cc_number = index
        cc_value = int(value * 127)
        self.client.send_cc(cc_number, cc_value, layer)

    def set_encoder_value(self, layer: int, index: int, value: float):
        cc_number = index + self.encoder_cc_start
        cc_value = int(value * 127)
        self.client.send_cc(cc_number, cc_value, layer)

    def set_button_state(self, layer: int, index: int, value: bool):
        velocity = 127 if value else 0
        self.client.send_note_on(index, velocity, layer)

    def set_encoder_mode(self, index: int, mode: int):
        """
        0 = Single
        1 = Pan
        2 = Fan
        3 = Spread
        4 = Trim
        5-127 = ignored
        """

        cc_number = index + self.encoder_cc_start
        self.client.send_cc(cc_number, mode, self.global_channel)

    def set_encoder_ring(self, index: int, value: float, blink=False, single=True):
        """
        0 = all LEDs off
        1-13 = LEDs 1 (left) - 13 (right) on
        14-26 = LEDs 1 (left) - 13 (right) blinking
        27 = all LEDs on
        28 = all LEDs blinking
        29-127 = ignored
        """

        cc_number = index + self.encoder_cc_start
        if single:
            cc_value = min(max(int(value * 13), 1), 13)
            if blink:
                cc_value += 13
        else:
            cc_value = 28 if blink else 27

        self.client.send_cc(cc_number, cc_value, self.global_channel)

    def set_button_mode(self, index: int, on=True, blink=False):
        """
        Note on with Velocity 0-1: Button LED off
        Note on with Velocity 2: Button LED on
        Note on with Velocity 3: Button LED blinking
        Note on with Velocity 4-127: ignored
        """

        velocity = on << 1 | blink
        self.client.send_note_on(index, velocity, self.global_channel)
