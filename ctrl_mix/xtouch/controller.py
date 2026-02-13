import asyncio
from collections.abc import Callable

from ctrl_mix.core.controller import Control
from ctrl_mix.core.events import Event, EventEmitter
from ctrl_mix.xtouch.control import Button, ControlSubType, ControlType, Encoder, Fader, XTouchControl
from ctrl_mix.xtouch.midi import MidiCtrlEvent, XTouchMidiAdapter


class XTouchController(EventEmitter):
    """
    Hardware API for handling and accessing individual controls
    """

    ControlChanged = Event[Callable[[XTouchControl, ControlSubType], None]]("ControlChanged")

    ButtonPressed = Event[Callable[[Button, ControlSubType], None]]("ButtonPressed")
    ButtonPressed = Event[Callable[[Button, ControlSubType], None]]("ButtonPressed")
    ButtonReleased = Event[Callable[[Button, ControlSubType], None]]("ButtonReleased")

    FaderMoved = Event[Callable[[Fader, ControlSubType], None]]("FaderMoved")
    FaderPressed = Event[Callable[[Fader, ControlSubType], None]]("FaderPressed")
    FaderReleased = Event[Callable[[Fader, ControlSubType], None]]("FaderReleased")

    EncoderMoved = Event[Callable[[Encoder, ControlSubType], None]]("EncoderMoved")
    EncoderPressed = Event[Callable[[Encoder, ControlSubType], None]]("EncoderPressed")
    EncoderLongPressed = Event[Callable[[Encoder, ControlSubType], None]]("EncoderLongPressed")
    EncoderReleased = Event[Callable[[Encoder, ControlSubType], None]]("EncoderReleased")

    def __init__(self, event_loop) -> None:
        super().__init__()

        self.event_loop = event_loop

        self.adapter = XTouchMidiAdapter()
        self.adapter.on(XTouchMidiAdapter.MidiControlChanged, self.on_midi_ctrl_event)

        self.build_controls()
        self.init_controls()

    def build_controls(self):
        self.faders: list[list[Fader]] = [
            [Fader(l, i, self) for i in range(8 + 1)]
            for l in range(2)]
        self.channel_faders: list[Fader] = self.faders[0][:8] + self.faders[1][:8]
        self.main_faders: list[Fader] = [self.faders[0][8], self.faders[1][8]]

        self.encoders = [
            [Encoder(l, i, self) for i in range(16)]
            for l in range(2)]
        self.channel_encoders = self.encoders[0][:8] + self.encoders[1][:8]
        self.side_encoders = [self.encoders[0][8:16], self.encoders[1][8:16]]

        self.buttons = [
            [Button(l, i, self) for i in range(32 + 6 + 1)]
            for l in range(2)]
        self.channel_buttons = self.buttons[0][:32] + self.buttons[1][:32]
        self.main_buttons = [self.buttons[0][32], self.buttons[1][32]]
        self.mute_buttons = self.buttons[0][0:8] + self.buttons[1][0:8]
        self.select_buttons = self.buttons[0][24:32] + self.buttons[1][24:32] + self.main_buttons
        self.transport_buttons = self.buttons[0][33:] + self.buttons[1][33:]
        self.button_columns = [
            self.channel_buttons[l * 32 + ch:l * 32 + ch + 32:8]
            for l in range(2)
            for ch in range(8)
        ]

    def init_controls(self):
        """
        Turn off visual values of current layer
        without affecting controller values
        """

        for btn in self.buttons[0]:
            btn.set_led(False)

        for enc in self.encoders[0]:
            enc.set_ring(0)

    def set_control(self, control: Control, value):
        control.set_value(value)

    def get_control(self, ctrl_type: ControlType, layer: int, number: int) -> XTouchControl:
        if ctrl_type is ControlType.Encoder:
            return self.encoders[layer][number]
        elif ctrl_type is ControlType.Button:
            return self.buttons[layer][number]

        return self.faders[layer][number]

    def get_channel_strip(self, channel: int):
        encoder = self.channel_encoders[channel]
        fader = self.channel_faders[channel]
        mute = self.button_columns[channel][0]

        return encoder, fader, mute

    def on_midi_ctrl_event(
        self,
        ctrl_type: ControlType,
        sub_type: ControlSubType,
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

        elif ctrl.is_enabled:
            ctrl.set_value(value, False)

        else:
            ctrl._on_disabled()
            return

        event_name = ctrl_type.name + str(MidiCtrlEvent(midi_event).name)
        event = getattr(self, event_name)

        if event is self.EncoderPressed and isinstance(ctrl, Encoder):
            asyncio.run_coroutine_threadsafe(
                asyncio.sleep(.25),
                self.event_loop
            ).add_done_callback(
                lambda _: self._delayed_encoder_press_handler(ctrl, sub_type))

        else:
            self.emit(event, ctrl, sub_type)
            self.emit(self.ControlChanged, ctrl, sub_type)

    def _delayed_encoder_press_handler(self, ctrl: XTouchControl, sub_type: ControlSubType):
        if ctrl.is_pressed:
            event = self.EncoderLongPressed
        else:
            event = self.EncoderPressed

        self.emit(event, ctrl, sub_type)
        self.emit(self.ControlChanged, ctrl, sub_type)
