from core.core import Control
from motu_xtouch.core.mixer import Parameter


class AssignmentManager:
    def __init__(self) -> None:
        self.control_to_parameter: dict = {}
        self.parameter_to_control: dict = {}

    def load_config(self): ...

    def assign_parameter(self, control: Control, parameter):
        self.control_to_parameter[control] = parameter
        self.parameter_to_control[parameter] = control

    def get_parameter(self, control: Control):
        return self.control_to_parameter.get(control)

    def get_control(self, parameter: Parameter):
        return self.parameter_to_control.get(parameter)
