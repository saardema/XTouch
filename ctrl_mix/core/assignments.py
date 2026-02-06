from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
import toml

from ctrl_mix.core.mixer import SendChannel
from ctrl_mix.motu.channel import MotuAux, MotuAuxSendCapable, MotuGroup, MotuInput, MotuMixerChannel
from ctrl_mix.motu.mixer import MotuMixer


if TYPE_CHECKING:
    from ctrl_mix.motu.mixer import MotuParameter
    from ctrl_mix.xtouch.control import XTouchControl

MAP_FILE_NAME = "map.toml"
CONFIG_FILE_NAME = "config.toml"


class ChannelConfig:
    def __init__(self, data: dict[str, bool] = {}) -> None:
        self.fader = data.get("fader", True)


class SendChannelConfig(ChannelConfig):
    def __init__(self, data: dict[str, bool] = {}) -> None:
        super().__init__(data)
        self.send_enabled = data.get("send", True)


@dataclass
class BusBundle:
    channel: MotuMixerChannel
    cfg: ChannelConfig


@dataclass
class SendBusBundle(BusBundle):
    channel: SendChannel
    cfg: SendChannelConfig


class AssignmentManager:
    def __init__(self, mixer: MotuMixer) -> None:
        self.mixer = mixer

        self.inputs: dict[str, BusBundle] = {}
        self.aux: dict[str, SendBusBundle] = {}
        self.groups: dict[str, SendBusBundle] = {}

        self.bundles: dict[MotuMixerChannel, BusBundle] = {}
        self.sendable_aux: dict[int, MotuAux] = {}
        self.sendable_groups: dict[int, MotuGroup] = {}

        self.main_mix: dict[int, BusBundle] = {}

        self.control_to_parameter: dict[XTouchControl, MotuParameter] = {}
        self.parameter_to_control: dict[MotuParameter, XTouchControl] = {}

        self.config = {}
        self._map_dict = {}
        self.load_config()

    def get_config(self, chan: MotuMixerChannel):
        return self.bundles[chan].cfg

    def assign(self, control: XTouchControl, parameter: MotuParameter | None = None):
        if parameter is None:
            self.unassign(control)
            return

        self.control_to_parameter[control] = parameter
        self.parameter_to_control[parameter] = control

    def unassign(self, control: XTouchControl):
        if param := self.control_to_parameter.get(control):
            del self.control_to_parameter[control]
            del self.parameter_to_control[param]

    def get_parameter(self, control: XTouchControl):
        return self.control_to_parameter.get(control)

    def get_control(self, parameter: MotuParameter):
        return self.parameter_to_control.get(parameter)

    def assign_channel_strip(self, n: int, channel: MotuMixerChannel | None):
        if isinstance(channel, MotuAuxSendCapable):
            self.main_mix[n] = BusBundle(channel, ChannelConfig())
            self.bundles[channel] = self.main_mix[n]
        else:
            del self.main_mix[n]

    def load_config(self):
        with open(CONFIG_FILE_NAME, "r") as f:
            self.config = toml.load(f)
        self._parse_config()

        with open(MAP_FILE_NAME, "r") as f:
            self._map_dict = toml.load(f)
        self._parse_map()

    def save_map(self):
        with open(MAP_FILE_NAME, "w") as f:
            toml.dump(self._map_dict, f)

    def save_config(self):
        with open(CONFIG_FILE_NAME, "w") as f:
            toml.dump(self.config, f)

    def _parse_map(self):
        chan_nr = 0
        self.main_mix = {}

        for strip_def in self._map_dict["channel_strip"]:
            if strip_def.get("disabled"):
                continue

            if (strip_type := strip_def.get("type", "input")) == "input":
                strip = self.inputs.get(strip_def["src"])
            else:
                strip = self.groups.get(strip_def["src"])

            if strip:
                self.main_mix[chan_nr] = strip
            else:
                print(f"Warning: {strip_type} '{strip_def["src"]}' not found")

            chan_nr += 1

    def _parse_config(self):
        self.inputs, self.aux, self.groups = {}, {}, {}

        chan: MotuInput
        for chan in self.mixer.channels.values():
            data = self.config["mixer"]["inputs"].get(chan.name, {})
            bundle = BusBundle(chan, ChannelConfig(data))
            self.inputs[chan.name] = bundle
            self.bundles[chan] = bundle

        group: MotuGroup
        for group in self.mixer.groups.values():
            data = self.config["mixer"]["groups"].get(group.name, {})
            bundle = SendBusBundle(group, SendChannelConfig(data))
            self.groups[group.name] = bundle
            if bundle.cfg.send_enabled:
                self.sendable_groups[group.channel_number] = group
            self.bundles[group] = bundle

        aux: MotuAux
        for aux in self.mixer.aux.values():
            data = self.config["mixer"]["aux"].get(aux.name, {})
            bundle = SendBusBundle(aux, SendChannelConfig(data))
            self.aux[aux.name] = bundle
            if bundle.cfg.send_enabled:
                self.sendable_aux[aux.channel_number] = aux
            self.bundles[aux] = bundle
