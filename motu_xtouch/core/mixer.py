from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum


TParam = int | str | float | bool


class Parameter:
    def __init__(
        self,
        param_type: type[TParam],
        initial: TParam | None = None,
    ) -> None:

        self.param_type = param_type
        self.value: TParam = initial if initial is not None else param_type()

    def set_value(self, new_value: TParam):
        self.value = self.param_type(new_value)


class ChannelType(Enum):
    Input = 'chan'
    Group = 'group'
    Aux = 'aux'
    Main = 'main'


class Mixer(ABC):
    def __init__(self, n_channels: int, n_groups: int, n_aux: int):
        self.n_channels = n_channels
        self.n_groups = n_groups
        self.n_aux = n_aux

    @abstractmethod
    def set_parameter(self, param: Parameter, value: TParam): ...


class MixerChannel:
    channel_type: ChannelType

    def __init__(self, mixer: Mixer, channel_number: int, name: str = ""):
        self.name = name
        self.mixer = mixer
        self.channel_number = channel_number


class MainChannel(MixerChannel):
    channel_type = ChannelType.Main


class InputChannel(MixerChannel):
    channel_type = ChannelType.Input


class GroupChannel(MixerChannel):
    channel_type = ChannelType.Group


class AuxChannel(MixerChannel):
    channel_type = ChannelType.Aux
