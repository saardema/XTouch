from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum

from ctrl_mix import remap
from ctrl_mix.core.events import Event


TParam = int | str | float | bool


class Parameter(ABC):
    def __init__(
        self,
        key: str,
        param_type: type[TParam],
        cfg: ParamConfig,
        channel: MixerChannel,
        name: str
    ) -> None:

        self.name = name
        self.key = key
        self.param_type = param_type
        self.cfg = cfg
        self.channel = channel

    @property
    @abstractmethod
    def value(self) -> TParam: ...

    @value.setter
    @abstractmethod
    def value(self, value: TParam): ...

    @property
    @abstractmethod
    def normalized(self) -> float: ...

    @normalized.setter
    @abstractmethod
    def normalized(self, value: TParam): ...

    def _from_normalized(self, value):
        return self.cfg.denormalize(value)

    def _to_normalized(self, value):
        return self.cfg.normalize(value)


class ParamConfig:
    def __init__(
        self,
        type: str,
        default: str,
        enums: list[str],
        unit: str | None,
        min: float | None,
        max: float | None
    ):

        self.type = type
        self.default = default
        self.enums = enums
        self.unit = unit

        self.has_limit = min is not None or max is not None
        self.min = float('-inf') if min is None else min
        self.max = float('inf') if max is None else max

    def normalize(self, value):
        if not self.has_limit:
            return value

        return remap(value, self.min, self.max, 0, 1)

    def denormalize(self, value):
        if not self.has_limit:
            return value

        return remap(value, 0, 1, self.min, self.max)

    def clamp(self, value):
        return min(max(value, self.min), self.max)


class ChannelType(Enum):
    Input = 'chan'
    Group = 'group'
    Aux = 'aux'
    Main = 'main'
    Monitor = 'monitor'


class Mixer(ABC):
    ParameterSetFromMixer = Event[Callable[[Parameter], None]]("ParameterSetFromMixer")

    def __init__(self):
        self.channels: dict[int, InputChannel] = {}
        self.groups: dict[int, GroupChannel] = {}
        self.aux: dict[int, AuxChannel] = {}

        super().__init__()

    @abstractmethod
    def set_parameter(self, param: Parameter, value: TParam): ...

    def find(self, name: str, type="") -> MixerChannel | None:

        haystack = self.aux | self.groups | self.channels

        if type == "input":
            haystack = self.channels
        elif type == "group":
            haystack = self.groups
        elif type == "aux":
            haystack = self.aux

        for chan in haystack.values():
            if chan.name == name:
                return chan

        return None

    @property
    def sendable_groups(self):
        return {
            nr: group for nr, group in self.groups.items()
            if group.config.send_enabled
        }

    @property
    def sendable_aux(self):
        return {
            nr: aux for nr, aux in self.aux.items()
            if aux.config.send_enabled
        }


class MixerChannel(ABC):
    channel_type: ChannelType
    config: ChannelConfig
    fader: Parameter
    mute: Parameter

    def __init__(self, mixer: Mixer, channel_number: int, name: str = ""):
        self.name = name
        self.mixer = mixer
        self.channel_number = channel_number


class MonitorChannel(MixerChannel):
    channel_type = ChannelType.Monitor


class MainChannel(MixerChannel):
    channel_type = ChannelType.Main


class SendChannel(MixerChannel):
    config: SendChannelConfig


class GroupSendCapable(MixerChannel):
    group_sends: dict[int, Parameter]


class AuxSendCapable(MixerChannel):
    aux_sends: dict[int, Parameter]


class InputChannel(AuxSendCapable):
    channel_type = ChannelType.Input


class GroupChannel(SendChannel, AuxSendCapable):
    channel_type = ChannelType.Group


class AuxChannel(SendChannel):
    channel_type = ChannelType.Aux


class ChannelConfig:
    def __init__(self, data: dict[str, bool] = {}) -> None:
        self.fader = data.get("fader", True)


class SendChannelConfig(ChannelConfig):
    def __init__(self, data: dict[str, bool] = {}) -> None:
        super().__init__(data)
        self.send_enabled = data.get("send", True)
