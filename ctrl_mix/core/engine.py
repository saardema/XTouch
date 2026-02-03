from collections.abc import Callable
import re
from core.events import Event, EventEmitter
from ctrl_mix.core.assignments import AssignmentManager
from ctrl_mix.motu.mixer import MotuMixer
from ctrl_mix.motu.parameter import MotuParameter
from ctrl_mix.xtouch.control import Button, XTouchControl
from ctrl_mix.xtouch.controller import XTouchController


class ControllerState:
    def __init__(self) -> None:
        self.selected_channel: list[int] = [-1, -1]


class Engine(EventEmitter):

    ChannelUnselected = Event[Callable[[int, int], None]]("ChannelUnslected")
    ChannelSelected = Event[Callable[[int, int], None]]("ChannelSelected")
    ChannelReselected = Event[Callable[[int, int], None]]("ChannelReselected")

    def __init__(self):
        super().__init__()

        self.controller = XTouchController()
        self.mixer = MotuMixer()
        self.assignments = AssignmentManager(self.mixer)

        self.state = ControllerState()

        self.mixer.on(MotuMixer.ParameterSetFromMixer, self.parameter_updated)
        self.controller.on(XTouchController.ButtonPressed, self.on_button_press_start)
        self.controller.on(XTouchController.ControlChanged, self.control_updated)

    def on_button_press_start(self, btn: Button):
        if btn in self.controller.select_buttons:
            ch = self.controller.select_buttons.index(btn)
            ch = ch if ch < 16 else -1
            self.select_channel(btn.layer, ch)

    def assign(self, control: XTouchControl, param: MotuParameter | None = None):
        self.assignments.assign(control, param)
        self.controller.set_control(control, param.normalized if param else 0)

    def select_channel(self, layer: int, ch: int):
        prev = self.state.selected_channel[layer]

        if prev != -1 and ch != prev:
            self.controller.select_buttons[prev].set_value(False)

        if ch == -1 or ch >= len(self.assignments.main_mix):
            self.state.selected_channel[layer] = -1
            self.emit(Engine.ChannelUnselected, layer, prev)

            return

        if prev == ch:
            self.emit(Engine.ChannelReselected, layer, ch)

            return

        for btn in self.controller.select_buttons:
            if btn.layer == layer:
                btn.set_value(False, True)

        if ch != -1:
            self.controller.select_buttons[ch].set_value(True)

        self.state.selected_channel[layer] = ch
        self.emit(Engine.ChannelSelected, layer, ch)

    def control_updated(self, ctrl: XTouchControl):
        if param := self.assignments.get_parameter(ctrl):
            self.mixer.set_parameter(param, ctrl.value)
            # log_change(ctrl, param)

    def parameter_updated(self, param: MotuParameter):
        if control := self.assignments.get_control(param):
            self.controller.set_control(control, param.normalized)


_last_param = None


def log_change(ctrl, param, mixer):
    c = ctrl.__class__.__name__
    p_name = param.param_path
    if m := re.match(r"matrix/(group|aux)/(\d+)/send", param.param_path):
        send, c = m.group(1), m.group(2)
        src = mixer.aux if send == "aux" else mixer.groups
        p_name = f"{src[int(c)].name} {param.name}"

    global _last_param
    if param != _last_param:
        print()
        _last_param = param

    c = f"{c} {ctrl.index}"
    p = f"{param.channel.name} [{p_name}]"
    out = f"{c} >> {p} ="
    val = str(ctrl.value).ljust(10)

    if isinstance(ctrl.value, float):
        pre_pad = int(ctrl.value * 50)
        val = "|" + " " * pre_pad + "[  |  ]" + " " * (50 - pre_pad) + "|"

    print(f"{out} {val}", end="\r")
