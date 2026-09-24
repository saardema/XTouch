import toml
from os.path import isfile

from ctrl_mix.core.controller import Control
from ctrl_mix.core.mixer import AuxSendCapable, ChannelConfig, \
    Mixer, MixerChannel, Parameter, SendChannelConfig

MAP_FILE_NAME = "map.toml"


class AssignmentManager:
    def __init__(self, mixer: Mixer) -> None:
        self.mixer = mixer

        self.main_mix: dict[int, MixerChannel] = {}

        self.control_to_parameter: dict[Control, Parameter] = {}
        self.parameter_to_control: dict[Parameter, Control] = {}

        self._map_data = {}
        self._load_map()

    def assign(self, control: Control, parameter: Parameter | None = None):
        if parameter is None:
            self.unassign(control)
            return

        self.control_to_parameter[control] = parameter
        self.parameter_to_control[parameter] = control

    def unassign(self, control: Control):
        if param := self.control_to_parameter.get(control):
            del self.control_to_parameter[control]
            if param in self.parameter_to_control:
                del self.parameter_to_control[param]

    def get_parameter(self, control: Control):
        return self.control_to_parameter.get(control)

    def get_control(self, parameter: Parameter):
        return self.parameter_to_control.get(parameter)

    def assign_channel_strip(self, n: int, channel: MixerChannel | None):
        if isinstance(channel, AuxSendCapable):
            self.main_mix[n] = channel
        else:
            del self.main_mix[n]

    def _load_map(self):
        if not isfile(MAP_FILE_NAME):
            self.save_map()

        with open(MAP_FILE_NAME, "r") as f:
            self._map_data = toml.load(f)
        self._parse_map()

    def save_map(self):
        with open(MAP_FILE_NAME, "w") as f:
            toml.dump(self._map_data, f)

    def _parse_map(self):
        chan_nr = 0
        self.main_mix = {}

        for strip_def in self._map_data["channel_strip"]:
            if strip_def.get("disabled"):
                continue

            strip_type = strip_def.get("type", "input")
            strip = self.mixer.find(strip_def["src"], strip_type)

            if strip:
                self.main_mix[chan_nr] = strip
            else:
                print(f"Warning: {strip_type} '{strip_def["src"]}' not found")

            chan_nr += 1

        for chan in self.mixer.channels.values():
            data = self._map_data["mixer"]["inputs"].get(chan.name, {})
            chan.config = ChannelConfig(data)

        for group in self.mixer.groups.values():
            data = self._map_data["mixer"]["groups"].get(group.name, {})
            group.config = SendChannelConfig(data)

        for aux in self.mixer.aux.values():
            data = self._map_data["mixer"]["aux"].get(aux.name, {})
            aux.config = SendChannelConfig(data)
