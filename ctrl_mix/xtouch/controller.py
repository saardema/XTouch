from collections.abc import Callable

from ctrl_mix.core.controller import Control
from ctrl_mix.core.events import Event, EventEmitter
from ctrl_mix.xtouch.control import Button, ControlType, Encoder, Fader, XTouchControl
from ctrl_mix.xtouch.midi import MidiCtrlEvent, XTouchMidiAdapter


class XTouchController(EventEmitter):
    ControlChanged = Event[Callable[[XTouchControl], None]]("ControlChanged")

    ButtonPressed = Event[Callable[[Button], None]]("ButtonPressed")
    ButtonPressed = Event[Callable[[Button], None]]("ButtonPressed")
    ButtonReleased = Event[Callable[[Button], None]]("ButtonReleased")

    FaderMoved = Event[Callable[[Fader], None]]("FaderMoved")
    FaderPressed = Event[Callable[[Fader], None]]("FaderPressed")
    FaderReleased = Event[Callable[[Fader], None]]("FaderReleased")

    EncoderMoved = Event[Callable[[Encoder], None]]("EncoderMoved")
    EncoderPressed = Event[Callable[[Encoder], None]]("EncoderPressed")
    EncoderReleased = Event[Callable[[Encoder], None]]("EncoderReleased")

    def __init__(self) -> None:
        super().__init__()

        self.adapter = XTouchMidiAdapter()
        self.adapter.on(XTouchMidiAdapter.MidiControlChanged, self.on_midi_ctrl_event)

        self.init_controls()

        for btn in self.channel_buttons:
            btn.set_led(False)

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
        self.side_encoders = [self.encoders[0][8:16], self.encoders[1][8:16]]

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
        control.sync()

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
        midi_event: MidiCtrlEvent,
        layer: int,
        number: int,
        value: float
    ):
        ctrl = self.get_control(ctrl_type, layer, number)

        if midi_event & MidiCtrlEvent.PressEvent:
            if midi_event is MidiCtrlEvent.Pressed:
                ctrl.on_press()
            else:
                ctrl.on_release()
        else:
            ctrl.set_value(value)

        event_name = ctrl_type.name + str(MidiCtrlEvent(midi_event).name)
        event = getattr(self, event_name)
        self.emit(event, ctrl)

        self.emit(self.ControlChanged, ctrl)
