from core.assignments import AssignmentManager
from motu.mixer import MotuMixer, MotuParameter
from core.core import Control, ControlEventFlags
from xtouch.controller import XTouchController


def control_updated(ctrl: Control, event: ControlEventFlags, value: float):
    if param := assignments.get_parameter(ctrl):
        if event & ControlEventFlags.Move:
            mixer.set_parameter(param, value, True)
            print(param)


def parameter_updated(param: MotuParameter):
    print(param)


if __name__ == "__main__":

    assignments = AssignmentManager()
    mixer = MotuMixer(parameter_updated)
    controller = XTouchController(control_updated)

    for i, chan in enumerate(list(mixer.channels.values())[:8]):
        assignments.assign_parameter(controller.faders[i], chan.fader)
        assignments.assign_parameter(controller.encoders[i + 8], chan.fader)

    # loop = asyncio.new_event_loop()
    # loop.run_forever()
