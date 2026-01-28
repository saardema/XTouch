import asyncio
from core.assignments import AssignmentManager
from motu.mixer import MotuMixer
from core.core import Control, ControlEventFlags
from xtouch.controller import XTouchController


def control_updated(ctrl: Control, event: ControlEventFlags, value: float):
    if param := assignments.get_parameter(ctrl):
        if event & ControlEventFlags.Move:
            mixer.set_parameter(param, value)


if __name__ == "__main__":

    assignments = AssignmentManager()
    mixer = MotuMixer()
    controller = XTouchController(control_updated)

    for i in range(8):
        assignments.assign_parameter(controller.faders[i], mixer.channels[i].fader)

    # loop = asyncio.new_event_loop()
    # loop.run_forever()
