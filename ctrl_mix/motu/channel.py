from __future__ import annotations

from typing import TYPE_CHECKING, Any
from ctrl_mix.core.mixer import AuxChannel, GroupChannel, InputChannel, MainChannel, MixerChannel, TParam
from ctrl_mix.motu.parameter import MotuParameter

if TYPE_CHECKING:
    from ctrl_mix.motu.mixer import MotuMixer


class MotuMixerChannel(MixerChannel):
    mixer: MotuMixer
    fader: MotuParameter
    mute: MotuParameter

    def setup(self):
        self.path = self.get_path()
        self.params: dict[str, MotuParameter | dict[str, MotuParameter]] = {}
        self.param_defs: dict[str, str | dict[int, str]] = {}
        self.param_defs["fader"] = "matrix/fader"
        self.param_defs["mute"] = "matrix/mute"

    def get_path(self):
        return f"{self.channel_type.value}/{self.channel_number}"

    def init_params(self, state: dict[str, TParam]):
        for attr, path_data in self.param_defs.items():
            if isinstance(path_data, str):
                param = MotuParameter.create(self, path_data, state)

                self.params[param.param_path] = param
                self.mixer.params[param.path] = param
                setattr(self, attr, param)

            elif isinstance(path_data, dict):
                params: dict[int, MotuParameter] = {}

                for i, sub_path in path_data.items():
                    params[i] = MotuParameter.create(self, sub_path, state)
                    self.params[params[i].param_path] = params[i]
                    self.mixer.params[params[i].path] = params[i]

                setattr(self, attr, params)

    def set_from_state(self, state: dict[str, Any]):
        for param_data in self.params.values():
            if isinstance(param_data, MotuParameter):
                if param_data.path in state:
                    param_data.value = state[param_data.path]

            elif isinstance(param_data, dict):
                for param in param_data.values():
                    if param.path in state:
                        param.value = state[param.path]

    def __repr__(self) -> str:
        props = [str(self.channel_number), str(self.fader._value)]

        if self.name:
            props.insert(0, self.name)

        return f"{self.__class__.__name__}({", ".join(props)})"


class MotuMainSendCapable(MotuMixerChannel):
    main_send: MotuParameter

    def setup(self):
        super().setup()
        self.param_defs["main_send"] = "matrix/main/0/send"


class MotuGroupSendCapable(MotuMixerChannel):
    group_sends: dict[int, MotuParameter]

    def setup(self):
        super().setup()
        self.param_defs["group_sends"] = {
            i: f"matrix/group/{i}/send"
            for i in self.mixer.group_bank
        }


class MotuAuxSendCapable(MotuMixerChannel):
    aux_sends: dict[int, MotuParameter]

    def setup(self):
        super().setup()
        self.param_defs["aux_sends"] = {
            i: f"matrix/aux/{i}/send"
            for i in self.mixer.aux_bank
        }


class MotuSendReceiver(MotuMixerChannel):
    prefader: MotuParameter

    def setup(self):
        super().setup()
        self.param_defs["prefader"] = "matrix/prefader"


class MotuMain(MotuMixerChannel, MainChannel):
    ...


class MotuInput(MotuMainSendCapable, MotuGroupSendCapable, MotuAuxSendCapable, InputChannel):
    ...


class MotuGroup(MotuMainSendCapable, MotuAuxSendCapable, MotuSendReceiver, GroupChannel):
    ...


class MotuAux(MotuSendReceiver, AuxChannel):
    ...
