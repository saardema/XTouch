from __future__ import annotations
from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
import math

from motu_xtouch.core.mixer import AuxChannel, GroupChannel, InputChannel, MainChannel, Mixer, Parameter, MixerChannel, TParam
from motu_xtouch.motu.store import MixerStore

N_CHANNELS = 48
N_GROUPS = 6
N_AUX = 14


class MotuParameter(Parameter):
    def __init__(
            self,
            channel: MotuMixerChannel,
            path: str,
            param_type: type[TParam],
            initial: TParam | None = None,
            is_log: bool = True
    ) -> None:

        super().__init__(param_type, initial)

        self.path = "/".join([channel.path, path])
        self.name = path.split("/")[-1]
        self.is_log = is_log

    def __repr__(self) -> str:
        return f"Parameter({self.name}={self.value})"

    def set_from_state(self, state: dict):
        if self.path in state:
            super().set_value(state[self.path])

    def set_value(self, new_value: TParam):
        if isinstance(new_value, float):
            new_value = self.lin_to_log(new_value)

        self.value = self.param_type(new_value)

    @staticmethod
    def lin_to_log(value: float) -> float:
        gain = value * 127 / 100
        exp = -8 + gain * 8
        f = 2 ** exp
        f -= 2 ** -8

        return min(max(f, 0), 4)

    @staticmethod
    def log_to_lin(value: float) -> float:
        value += 2 ** -8
        exp = math.log2(value)
        gain = 1 - exp / -8
        value = gain * 100 / 127

        value = int(min(max(value, 0), 127))

        return value


class MotuMixer(Mixer):
    def __init__(self) -> None:
        super().__init__(N_CHANNELS, N_AUX, N_GROUPS)

        self.store = MixerStore()
        mix_state = self.store.mix_state

        self.main = MotuMain(self, 0, "Main")
        self.main.setup()
        self.main.set_from_state(mix_state)

        self.channels: dict[int, MotuInput] = {}
        self.init_bank(self.channels, "chan", MotuInput, mix_state)

        self.groups: dict[int, MotuGroup] = {}
        self.init_bank(self.groups, "group", MotuGroup, mix_state)

        self.aux: dict[int, MotuAux] = {}
        self.init_bank(self.aux, "aux", MotuAux, mix_state)

    def init_bank(self, target: dict, bank_name: str, cls: type[MotuMixerChannel], mix_state: dict):
        for i in range(len(self.store.banks[bank_name])):
            name = self.store.banks[bank_name][i].name
            target[i] = cls(self, i, name)
            target[i].setup()
            target[i].set_from_state(mix_state)

    def set_parameter(self, param: MotuParameter, ctrl_value: float):
        param.set_value(ctrl_value)
        self.store.push_change(param.path, param.value)
        # print(param.path, param.name, ctrl_value)


class MotuMixerChannel(MixerChannel):

    def setup(self):
        self.path = self.get_path()
        self.fader = MotuParameter(self, "matrix/fader", float)
        self.mute = MotuParameter(self, "matrix/mute", bool)

    def get_path(self):
        return f"{self.channel_type.value}/{self.channel_number}"

    def set_from_state(self, state: dict[str, TParam]):
        self.fader.set_from_state(state)
        self.mute.set_from_state(state)

    def __repr__(self) -> str:
        props = [str(self.channel_number), str(self.fader.value)]

        if self.name:
            props.insert(0, self.name)

        return f"{self.__class__.__name__}({", ".join(props)})"


class MotuMainSendCapable(MotuMixerChannel):

    def setup(self):
        super().setup()

        self.main_send = MotuParameter(self, "matrix/main/0/send", float)

    def set_from_state(self, state: dict[str, TParam]):
        super().set_from_state(state)

        self.main_send.set_from_state(state)


class MotuGroupSendCapable(MotuMixerChannel):

    def setup(self):
        super().setup()

        self.group_sends: dict[int, MotuParameter] = {
            i: MotuParameter(self, f"matrix/group/{i}/send", float)
            for i in range(self.mixer.n_groups)
        }

    def set_from_state(self, state: dict[str, TParam]):
        super().set_from_state(state)

        for send in self.group_sends.values():
            send.set_from_state(state)


class MotuAuxSendCapable(MotuMixerChannel):

    def setup(self):
        super().setup()

        self.aux_sends: dict[int, MotuParameter] = {
            i: MotuParameter(self, f"matrix/aux/{i}/send", float)
            for i in range(self.mixer.n_aux)
        }

    def set_from_state(self, state: dict[str, TParam]):
        super().set_from_state(state)

        for send in self.aux_sends.values():
            send.set_from_state(state)


class MotuSendReceiver(MotuMixerChannel):

    def setup(self):
        super().setup()

        self.prefader = MotuParameter(self, "matrix/prefader", bool)

    def set_from_state(self, state: dict[str, TParam]):
        super().set_from_state(state)

        self.prefader.set_from_state(state)


class MotuMain(MotuMixerChannel, MainChannel):
    def setup(self):
        self.path = f"main/0"
        super().setup()


class MotuInput(MotuMainSendCapable, MotuGroupSendCapable, InputChannel):
    def setup(self):
        self.path = f"ch/{self.channel_number}"
        super().setup()


class MotuGroup(MotuMainSendCapable, MotuAuxSendCapable, MotuSendReceiver, GroupChannel):
    def setup(self):
        self.path = f"group/{self.channel_number}"
        super().setup()


class MotuAux(MotuSendReceiver, AuxChannel):
    def setup(self):
        self.path = f"aux/{self.channel_number}"
        super().setup()
