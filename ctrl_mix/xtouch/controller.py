from collections.abc import Callable
from dataclasses import dataclass, field

from ctrl_mix.core.events import EventEmitter
from ctrl_mix.xtouch.control import Button, ControlType, Encoder, Fader, XTouchControl
from ctrl_mix.xtouch.midi import CtrlEvent, XTouchMidiAdapter


@dataclass
class ControllerState:
    selected_channel: list[int] = field(default_factory=lambda: [-1, -1])


class XTouchController(EventEmitter):
    def __init__(self, callback: Callable[[XTouchControl], None]) -> None:
        super().__init__()

        self.adapter = XTouchMidiAdapter(self.on_midi_ctrl_event)
        self.ctrl_change_callback = callback
        self.state = ControllerState()

        self.init_controls()

    def init_controls(self):
        self.faders: list[list[Fader]] = [
            [Fader(l, i, self.adapter) for i in range(8 + 1)]
            for l in range(2)]
        self.channel_faders: list[Fader] = self.faders[0][:8] + self.faders[1][:8]
        self.main_faders: list[Fader] = [self.faders[0][8], self.faders[1][8]]

        self.encoders = [
            [Encoder(l, i, self.adapter) for i in range(16)]
            for l in range(2)]
        self.channel_encoders = self.encoders[0][:8] + self.encoders[1][:8]
        self.side_encoders = self.encoders[0][8:16] + self.encoders[1][8:16]
        # for enc in self.side_encoders:
        #     enc.layer = 0

        self.buttons = [
            [Button(l, i, self.adapter) for i in range(32 + 6 + 1)]
            for l in range(2)]
        self.channel_buttons = self.buttons[0][:32] + self.buttons[1][:32]
        self.main_buttons = [self.buttons[0][32], self.buttons[1][32]]
        self.select_buttons = self.buttons[0][24:32] + self.buttons[1][24:32] + self.main_buttons
        self.transport_buttons = self.buttons[0][33:] + self.buttons[1][33:]
        self.button_columns = [
            self.channel_buttons[l * 32 + ch:l * 32 + ch + 32:8]
            for l in range(2)
            for ch in range(8)
        ]

    def set_control(self, control: XTouchControl, value):
        control.set_value(value)

    def get_channel_strip(self, channel: int):
        encoder = self.channel_encoders[channel]
        fader = self.channel_faders[channel]
        mute = self.button_columns[channel][0]

        return encoder, fader, mute

    def get_control(self, ctrl_type: ControlType, layer: int, number: int) -> XTouchControl:
        if ctrl_type is ControlType.Encoder:
            return self.encoders[layer][number]
        elif ctrl_type is ControlType.Button:
            return self.buttons[layer][number]

        return self.faders[layer][number]

    def on_midi_ctrl_event(
        self,
        ctrl_type: ControlType,
        event: CtrlEvent,
        layer: int,
        number: int,
        value: float
    ):
        ctrl = self.get_control(ctrl_type, layer, number)

        if event & CtrlEvent.Press:
            if event & CtrlEvent.Start:
                ctrl.on_press()
                if isinstance(ctrl, Button):
                    self.on_button_press_start(ctrl)
            else:
                ctrl.on_release()
        else:
            ctrl.sync_value(value)

        self.ctrl_change_callback(ctrl)

    def on_button_press_start(self, btn: Button):
        if btn in self.select_buttons:
            ch = self.select_buttons.index(btn)
            ch = ch if ch < 16 else -1
            self.select_channel(btn.layer, ch)

    def select_channel(self, layer: int, ch: int):
        prev = self.state.selected_channel[layer]

        if prev == ch:
            return

        if prev != -1:
            self.select_buttons[prev].set_state(False)

        if ch != -1:
            self.select_buttons[ch].set_state(True)

        self.state.selected_channel[layer] = ch
        self.emit("select_channel", layer, ch)
