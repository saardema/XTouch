from dataclasses import dataclass
import toml
from typing import Any
from core.core import Control
from motu_xtouch.core.mixer import Parameter

MAP_FILE_NAME = "map.toml"
CONFIG_FILE_NAME = "config.toml"


class ChannelStrip:
    def __init__(self, chan_nr: int, cfg: dict[str, Any]):
        self.chan_nr = chan_nr
        self.name: str = cfg["src"]
        self.type: str = cfg.get("type", "input")


@dataclass
class ChannelConfig:
    def __init__(self, name: str, cfg: dict[str, Any]):
        self.name: str = name
        self.hot_bar: bool = cfg.get("hot_bar", True)
        self.disabled: bool = cfg.get("disabled", False)


class AssignmentManager:
    def __init__(self, ins, groups, aux) -> None:
        self.input_bank, self.group_bank, self.aux_bank = ins, groups, aux
        self.inputs, self.aux, self.groups = {}, {}, {}
        self.strips = []

        self.control_to_parameter: dict = {}
        self.parameter_to_control: dict = {}

        self.config = {}
        self.channel_strip_mapping = {}
        self.load_config()
        self.save_map()

    def load_config(self):
        with open(MAP_FILE_NAME, "r") as f:
            self.channel_strip_mapping = toml.load(f)

        with open(CONFIG_FILE_NAME, "r") as f:
            self.config = toml.load(f)

        self._parse_config()

    def save_map(self):
        with open(MAP_FILE_NAME, "w") as f:
            toml.dump(self.channel_strip_mapping, f)

    def save_config(self):
        with open(CONFIG_FILE_NAME, "w") as f:
            toml.dump(self.config, f)

    def _parse_config(self):
        self.inputs, self.aux, self.groups = {}, {}, {}

        for chan in self.input_bank.values():
            data = self.config["mixer"]["inputs"].get(chan.name, {})
            self.inputs[chan.name] = ChannelConfig(chan.name, data)

        for chan in self.group_bank.values():
            data = self.config["mixer"]["groups"].get(chan.name, {})
            self.groups[chan.name] = ChannelConfig(chan.name, data)

        for chan in self.aux_bank.values():
            data = self.config["mixer"]["aux"].get(chan.name, {})
            self.aux[chan.name] = ChannelConfig(chan.name, data)

    def assign_parameter(self, control: Control, parameter):
        self.control_to_parameter[control] = parameter
        self.parameter_to_control[parameter] = control

    def get_parameter(self, control: Control):
        return self.control_to_parameter.get(control)

    def get_control(self, parameter: Parameter):
        return self.parameter_to_control.get(parameter)
