from core.assignments import AssignmentManager
from motu.mixer import MotuMixer, MotuParameter
from core.core import Control, ControlEventFlags
from xtouch.controller import XTouchController


def control_updated(ctrl: Control, event: ControlEventFlags, value: float):
    if param := assignments.get_parameter(ctrl):
        mixer.set_parameter(param, ctrl.value, True)


def parameter_updated(param: MotuParameter):
    if control := assignments.get_control(param):
        controller.on_parameter_change(control, param.value)


if __name__ == "__main__":
    controller = XTouchController(control_updated)
    mixer = MotuMixer(parameter_updated)
    assignments = AssignmentManager(mixer.input_bank, mixer.group_bank, mixer.aux_bank)

    chans = [
        mixer.channels[2],   # TR-8S Mix
        mixer.channels[4],   # TR-8S Kick
        mixer.channels[5],   # Sub-37
        mixer.channels[6],   # Labyrinth
        mixer.channels[10],  # Digitakt
        mixer.channels[12],  # Minilogue XD
        mixer.channels[20],  # FX Return
        mixer.channels[18],  # Mac
    ]

    for i, chan in enumerate(chans):
        assignments.assign_parameter(controller.faders[i], chan.fader)
        assignments.assign_parameter(controller.encoders[i], chan.group_sends[0])
        assignments.assign_parameter(controller.buttons[i], chan.mute)
        controller.buttons[i].is_toggle = True

    assignments.assign_parameter(controller.faders[16], mixer.main.fader)

    for control, parameter in assignments.control_to_parameter.items():
        controller.on_parameter_change(control, parameter.value)
