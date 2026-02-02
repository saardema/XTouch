from core.assignments import AssignmentManager
from ctrl_mix.core.mixer import InputChannel
from motu.mixer import MotuGroup, MotuInput, MotuMixer, MotuParameter
from ctrl_mix import gain_to_norm, norm_to_gain
from xtouch.control import XTouchControl
from xtouch.controller import XTouchController


def normalize_param(param: MotuParameter):
    if param.is_gain() and isinstance(param.value, float):
        return gain_to_norm(param.value)

    return param.value


def normalize_ctrl(param: MotuParameter, ctrl: XTouchControl):
    if param.is_gain() and isinstance(param.value, float):
        return norm_to_gain(ctrl.value)

    return ctrl.value


def control_updated(ctrl: XTouchControl):
    if param := assignments.get_parameter(ctrl):
        mixer.set_parameter(param, normalize_ctrl(param, ctrl))


def parameter_updated(param: MotuParameter):
    if control := assignments.get_control(param):
        controller.set_control(control, normalize_param(param))


def setup_strips():
    for i, strip in assignments.main_mix.items():
        encoder, fader, button = controller.get_channel_strip(i)

        # Fader => Channel strip fader
        assignments.assign_parameter(fader, strip.channel.fader)

        # Top encoder => Group sends
        if isinstance(strip.channel, MotuInput):
            assignments.assign_parameter(encoder, strip.channel.group_sends[0])

        # Bottom button => Mute toggle
        assignments.assign_parameter(button, strip.channel.mute)
        button.is_toggle = True


def on_channel_selected(layer: int, ch: int):
    if ch >= len(assignments.main_mix):
        ch = -1
        controller.select_channel(layer, ch)

    encoders = controller.side_encoders[layer * 8:layer * 8 + 8]

    if ch == -1:
        for enc in encoders:
            assignments.unassign_control(enc)
            controller.set_control(enc, 0)

        return

    chan = assignments.main_mix[ch].channel

    for enc, aux in zip(encoders, avail_aux_ch):
        if isinstance(chan, (MotuInput, MotuGroup)):
            param = chan.aux_sends[aux.channel_number]
            assignments.assign_parameter(enc, param)
            controller.set_control(enc, normalize_param(param))


if __name__ == "__main__":
    controller = XTouchController(control_updated)
    mixer = MotuMixer(parameter_updated)
    assignments = AssignmentManager(mixer)
    avail_aux_ch = [aux.channel for aux in assignments.aux.values() if aux.cfg.send]
    avail_groups = [aux.channel for aux in assignments.aux.values() if aux.cfg.send]

    mixer.apply_state()

    setup_strips()

    controller.on("select_channel", on_channel_selected)

    # Main mix fader
    assignments.assign_parameter(controller.main_faders[0], mixer.main.fader)
    mixer.main.fader.max_val = 1.0

    # Initialize controller value to its parameter value
    for control, parameter in assignments.control_to_parameter.items():
        controller.set_control(control, normalize_param(parameter))
