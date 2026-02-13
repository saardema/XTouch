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

    def __init__(self, n_channels: int, n_groups: int, n_aux: int):
        self.n_channels = n_channels
        self.n_groups = n_groups
        self.n_aux = n_aux
        self.channels: dict[int, InputChannel] = {}
        self.groups: dict[int, GroupChannel] = {}
        self.aux: dict[int, AuxChannel] = {}

        super().__init__()

    @abstractmethod
    def set_parameter(self, param: Parameter, value: TParam): ...


class MixerChannel:
    channel_type: ChannelType
    fader: Parameter
    mute: Parameter

    def __init__(self, mixer: Mixer, channel_number: int, name: str = ""):
        self.name = name
        self.mixer = mixer
        self.channel_number = channel_number


class MonitorChannel(MixerChannel):
    ...


class MainChannel(MixerChannel):
    ...


class SendChannel(MixerChannel):
    ...


class GroupSendCapable(MixerChannel):
    group_sends: dict[int, Parameter]


class AuxSendCapable(MixerChannel):
    aux_sends: dict[int, Parameter]


class InputChannel(AuxSendCapable):
    ...


class GroupChannel(SendChannel, AuxSendCapable):
    ...


class AuxChannel(SendChannel):
    ...
