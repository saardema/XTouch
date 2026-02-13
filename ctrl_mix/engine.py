import asyncio
from collections.abc import Callable, Sequence
from enum import Enum
import re

from core.events import Event, EventEmitter
from ctrl_mix.core.assignments import AssignmentManager
from ctrl_mix.core.mixer import Parameter
from ctrl_mix.motu.channel import MotuAuxSendCapable, MotuGroupSendCapable
from ctrl_mix.motu.mixer import MotuMixer
from ctrl_mix.motu.parameter import MotuParameter
from ctrl_mix.xtouch.control import Button, ControlSubType, Encoder, XTouchControl
from ctrl_mix.xtouch.controller import XTouchController

_last_log_param = None


def log_change(ctrl, param, mixer):
    c = ctrl.__class__.__name__
    p_name = param.rel_path
    if m := re.match(r"matrix/(group|aux)/(\d+)/send", p_name):
        send, c = m.group(1), m.group(2)
        src = mixer.aux if send == "aux" else mixer.groups
        p_name = f"{src[int(c)].name} {param.name}"

    global _last_log_param
    if param != _last_log_param:
        print()
        _last_log_param = param

    c = f"{c} {ctrl.index}"
    p = f"{param.channel.name} [{p_name}]"
    out = f"{c} >> {p} ="

    if param.name in ("send", "fader") and False:
        lpad = int(ctrl.value * 32)
        val = f"|{" " * lpad}[  |  ]{" " * (32 - lpad)}|"
    else:
        val = f"{param.value:.2f} {param.cfg.unit} [{ctrl.value:.3f}]"

    print(f"{out:42} {val:20}", end="\r")


class ChannelConfigMode(Enum):
    Off = -1
    AuxSends = 0
    EQ = 1
    Compressor = 2
    Gate = 3


class ControllerState:
    def __init__(self) -> None:
        self.selected_channel: list[int] = [-1, -1]
        self.chan_cfg_mode: ChannelConfigMode = ChannelConfigMode.Off
        self.layer: int = 0
        self._last_expression_value: int = 0


class Engine(EventEmitter):

    ChannelUnselected = Event[Callable[[int, int], None]]("ChannelUnslected")
    ChannelSelected = Event[Callable[[int, int], None]]("ChannelSelected")
    ChannelReselected = Event[Callable[[int, int], None]]("ChannelReselected")
    ChannelConfigModeChanged = Event[Callable[[ChannelConfigMode], None]]("ChannelConfigModeChanged")
    LayerChanged = Event[Callable[[int], None]]("LayerChanged")

    def __init__(self):
        super().__init__()

        self.event_loop = asyncio.new_event_loop()

        self.controller = XTouchController(self.event_loop)
        self.mixer = MotuMixer(self.event_loop)
        self.assignments = AssignmentManager(self.mixer)

        self.state = ControllerState()
        adapter = self.controller.adapter

        self.mixer.on(MotuMixer.ParameterSetFromMixer, self._on_parameter_updated)
        self.controller.on(XTouchController.ButtonPressed, self._on_button_press_start)
        self.controller.on(XTouchController.ControlChanged, self._on_control_updated)
        adapter.on(adapter.ExpressionChanged, self._on_expression_changed)

    def set_chan_cfg_mode(self, mode: ChannelConfigMode):
        prev = self.state.chan_cfg_mode
        self.state.chan_cfg_mode = mode

        for m in ChannelConfigMode:
            if m != ChannelConfigMode.Off:
                idx = self.state.layer * 6 + m.value
                self.controller.transport_buttons[idx].set_value(mode == m)

        if prev != mode:
            self.emit(Engine.ChannelConfigModeChanged, prev)

    def assign(self, control: XTouchControl, param: Parameter | None = None, sync=True):
        self.assignments.assign(control, param)

        if param and isinstance(control, Encoder):
            if param.cfg.min and param.cfg.min < 0 and \
                    param.cfg.max and param.cfg.max > 0:
                control.set_mode(Encoder.Mode.Trim, sync)
            elif param.name in ("freq"):
                control.set_mode(Encoder.Mode.Single, sync)
            elif param.name in ("bw"):
                control.set_mode(Encoder.Mode.Spread, sync)
            else:
                control.set_mode(Encoder.Mode.Fan, sync)
        if sync:
            control.is_enabled = bool(param)

        sync_value = sync and control.layer == self.state.layer
        control.set_value(param.normalized if param else 0.0, sync_value)

    def select_channel(self, layer: int, ch: int):
        # Select inactive channel > ignore
        if ch >= len(self.assignments.main_mix):
            return

        prev = self.state.selected_channel[layer]
        self.state.selected_channel[layer] = ch

        # Switch off previous button
        if prev not in (-1, ch):
            self.controller.select_buttons[prev].set_value(False)

        # Unselect (switch to main/default selection)
        if ch == -1:
            if prev != -1:
                self.emit(Engine.ChannelUnselected, layer, prev)

            return

        # Reselect current
        if prev == ch:
            self.emit(Engine.ChannelReselected, layer, ch)

            return

        self.controller.select_buttons[ch].set_value(True)

        self.emit(Engine.ChannelSelected, layer, ch)

    def assign_encoders(self, channel: bool, params: Sequence[MotuParameter | None], layer: int | None = None):
        encs = self.controller.channel_encoders
        if not channel:
            encs = self.controller.side_encoders[0] + self.controller.side_encoders[1]

        if layer is not None:
            encs = encs[layer * 8:layer * 8 + 8]

        for enc in encs:
            i = enc.index % 8
            param = params[i] if i < len(params) else None
            self.assign(enc, param)

    def get_main_out_channels(self):
        return [
            chan.fader for chan in self.mixer.aux.values()
            if chan.name in ("Aux JBL", "Aux Sub")
        ] + [self.mixer.monitor.fader]

    def get_aux_sends(self, chan: MotuAuxSendCapable):
        return [chan.aux_sends[a]["send"] for a in self.assignments.sendable_aux]

    def get_group_sends(self, chan: MotuGroupSendCapable):
        return [
            send["send"] for nr, send in chan.group_sends.items()
            if nr in self.assignments.sendable_groups]

    def _set_layer(self, layer: int):
        if self.state.layer != layer:
            print("Switched to layer", ["A", "B"][layer])
            self.state.layer = layer
            self.select_channel(layer, self.state.selected_channel[layer])
            self.set_chan_cfg_mode(self.state.chan_cfg_mode)
            self.emit(Engine.LayerChanged, layer)

    def _on_button_press_start(self, btn: Button, sub_type: ControlSubType):
        if btn in self.controller.select_buttons:
            ch = self.controller.select_buttons.index(btn)
            ch = ch if ch < 16 else -1
            self.select_channel(btn.layer, ch)

        elif sub_type is ControlSubType.Transport:
            idx = self.controller.transport_buttons.index(btn) % 6
            if idx in ChannelConfigMode:
                self.set_chan_cfg_mode(ChannelConfigMode(idx))

    def _on_expression_changed(self, value: int):
        f0, f1 = self.controller.main_faders

        if f0.is_pressed or f1.is_pressed:
            return

        e0, e1 = f0.value * 6.1, f1.value * 6.1
        d0, d1 = abs(e0 - value), abs(e1 - value)
        self._set_layer(int(d0 > d1))

    def _on_control_updated(self, ctrl: XTouchControl, sub_type: ControlSubType):
        self._set_layer(ctrl.layer)

        if param := self.assignments.get_parameter(ctrl):
            self.mixer.set_parameter(param, ctrl.value)
            log_change(ctrl, param, self.mixer)

    def _on_parameter_updated(self, param: Parameter):
        if control := self.assignments.get_control(param):
            self.controller.set_control(control, param.normalized)
