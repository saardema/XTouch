from __future__ import annotations
from collections.abc import Callable

from motu_xtouch import lin_to_log
from motu_xtouch.core.mixer import AuxChannel, GroupChannel, InputChannel, MainChannel, Mixer, Parameter, MixerChannel, TParam
from motu_xtouch.motu.store import AudioChannel, MixerStore


class MotuParameter(Parameter):
    def __init__(
            self,
            channel: MotuMixerChannel,
            path: str,
            mix_state: dict[str, TParam],
    ) -> None:

        self.channel = channel
        self.param_path = path
        self.path = "/".join([channel.path, path])
        self.name = path.split("/")[-1]

        param_type, initial = self.parse_config(mix_state)
        super().__init__(param_type, initial)

    def __repr__(self) -> str:
        return f"Parameter({self.path} = {self.value})"

    def set_from_state(self, state: dict, silent=False):
        if self.path in state:
            self.set_value(state[self.path], silent)

    def set_value(self, new_value: TParam, silent=False):
        self.value = self.param_type(new_value)
        if not silent:
            self.channel.mixer.on_parameter_change(self)

    def parse_config(self, mix: dict[str, TParam]):
        cfg_key = self.param_path
        if cfg_key.endswith("/send"):
            cfg_key = "matrix/fader"
        config = str(mix[f"ctrls/{cfg_key}"])

        cfg_type, initial = "", None
        min_val, max_val, unit = None, None, None

        match config.split(":"):
            case [cfg_type, initial, min_val, max_val, unit]: ...
            case [cfg_type, initial]: ...

        ptype = {"bool": bool, "int": int}.get(cfg_type, float)
        initial = ptype(initial) if initial is not None else ptype()
        self.min_val = ptype(min_val) if min_val is not None else None
        self.max_val = ptype(max_val) if max_val is not None else None
        self.unit = unit

        return ptype, initial


class MotuMixer(Mixer):
    def __init__(self, callback: Callable[[MotuParameter], None]) -> None:
        self.callback = callback
        self.store = MixerStore()

        self.input_bank = self.store.get_bank("Mix In")
        self.group_bank = self.store.get_bank("Mix Group")
        self.aux_bank = self.store.get_bank("Mix Aux")

        super().__init__(len(self.input_bank), len(self.group_bank), len(self.aux_bank))

        self.main = MotuMain(self, 0, "Main")
        self.main.setup()
        self.main.set_from_state(self.store.mix_state)

        self.channels: dict[int, MotuInput] = {}
        self.init_bank(self.channels, self.input_bank, MotuInput, self.store.mix_state)

        self.groups: dict[int, MotuGroup] = {}
        self.init_bank(self.groups, self.group_bank, MotuGroup, self.store.mix_state)

        self.aux: dict[int, MotuAux] = {}
        self.init_bank(self.aux, self.aux_bank, MotuAux, self.store.mix_state)

    def init_bank(self, target: dict, bank: dict[int, AudioChannel], cls: type[MotuMixerChannel], mix_state: dict):
        for i, chan in bank.items():
            target[i] = cls(self, i, chan.name)
            target[i].setup()
            target[i].set_from_state(mix_state)

    def set_parameter(self, param: MotuParameter, ctrl_value: float, silent=False):
        param.set_value(ctrl_value, silent)
        self.store.push_change(param.path, param.value)

    def on_parameter_change(self, param: MotuParameter):
        self.callback(param)


class MotuMixerChannel(MixerChannel):
    mixer: MotuMixer
    fader: MotuParameter
    mute: MotuParameter

    def setup(self):
        self.path = self.get_path()
        self.param_defs: dict[str, str | dict[int, str]] = {}
        self.param_defs["fader"] = "matrix/fader"
        self.param_defs["mute"] = "matrix/mute"

    def get_path(self):
        return f"{self.channel_type.value}/{self.channel_number}"

    def set_from_state(self, state: dict[str, TParam]):
        for key, path_data in self.param_defs.items():
            if isinstance(path_data, str):
                param = MotuParameter(self, path_data, state)
                param.set_from_state(state, True)
                setattr(self, key, param)

            elif isinstance(path_data, dict):
                params: dict[int, MotuParameter] = {}
                for i, sub_path in path_data.items():
                    params[i] = MotuParameter(self, sub_path, state)
                    params[i].set_from_state(state, True)

                setattr(self, key, params)

    def __repr__(self) -> str:
        props = [str(self.channel_number), str(self.fader.value)]

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
