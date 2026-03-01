from typing import TYPE_CHECKING, Any
from ctrl_mix.motu.parameter import MotuParameter
from ctrl_mix.core.mixer import AuxChannel, GroupChannel, InputChannel, \
    MainChannel, Mixer, MixerChannel, MonitorChannel

if TYPE_CHECKING:
    from ctrl_mix.motu.mixer import MotuMixer


class Equalizer:
    class Band:
        enable: MotuParameter
        freq: MotuParameter
        gain: MotuParameter
        bw: MotuParameter
        mode: MotuParameter

    def __init__(self) -> None:
        self.lowshelf = Equalizer.Band()
        self.mid1 = Equalizer.Band()
        self.mid2 = Equalizer.Band()
        self.highshelf = Equalizer.Band()

    def get_bands(self):
        return [self.lowshelf, self.mid1, self.mid2, self.highshelf]


class MotuMixerChannel(MixerChannel):
    mixer: MotuMixer
    fader: MotuParameter
    mute: MotuParameter

    def __init__(self, mixer: Mixer, channel_number: int, name: str = ""):
        super().__init__(mixer, channel_number, name)

        self.path = self.get_path()
        self.params = {}
        self.eq = Equalizer()

    def get_path(self):
        return f"{self.channel_type.value}/{self.channel_number}"

    def create_param(self, path: str):
        mix = self.mixer.store.mix_state
        param = MotuParameter.create(self, self.path, path, mix)
        self.mixer.params[f"{self.path}/{path}"] = param

        return param

    def init_params(self, state: dict[str, Any]):

        self.fader = self.create_param("matrix/fader")
        self.mute = self.create_param("matrix/mute")

        for band_key, attrs in state.get("eq", {}).items():
            band = getattr(self.eq, band_key)
            for attr in attrs:
                param = self.create_param(f"eq/{band_key}/{attr}")
                setattr(band, attr, param)

    def __repr__(self) -> str:
        props = [str(self.channel_number), str(self.fader.value)]
        props = [str(self.channel_number)]

        if self.name:
            props.insert(0, self.name)

        return f"{self.__class__.__name__}({", ".join(props)})"


class MotuMainSendCapable(MotuMixerChannel):
    main_send: MotuParameter

    def init_params(self, state: dict[str, Any]):
        super().init_params(state)

        self.main_send = self.create_param("matrix/main/0/send")


class MotuGroupSendCapable(MotuMixerChannel):
    group_sends: dict[int, dict[str, MotuParameter]]

    def init_params(self, state: dict[str, Any]):
        super().init_params(state)

        self.group_sends = {}

        for idx in state["matrix"]["group"]:
            self.group_sends[int(idx)] = {
                "send": self.create_param(f"matrix/group/{idx}/send"),
                "pan": self.create_param(f"matrix/group/{idx}/pan")
            }

        self.group_sends = dict(sorted(self.group_sends.items()))


class MotuAuxSendCapable(MotuMixerChannel):
    aux_sends: dict[int, dict[str, MotuParameter]]

    def init_params(self, state: dict[str, Any]):
        super().init_params(state)

        self.aux_sends = {}

        for idx in state["matrix"]["aux"]:
            self.aux_sends[int(idx)] = {
                "send": self.create_param(f"matrix/aux/{idx}/send"),
                "pan": self.create_param(f"matrix/aux/{idx}/pan")
            }

        self.aux_sends = dict(sorted(self.aux_sends.items()))


class MotuSendReceiver(MotuMixerChannel):
    prefader: MotuParameter

    def init_params(self, state: dict[str, Any]):
        super().init_params(state)

        self.prefader = self.create_param("matrix/prefader")


class MotuMonitor(MotuMixerChannel, MonitorChannel):
    ...


class MotuMain(MotuMixerChannel, MainChannel):
    ...


class MotuInput(MotuMainSendCapable, MotuAuxSendCapable, MotuGroupSendCapable, InputChannel):
    ...


class MotuGroup(MotuMainSendCapable, MotuAuxSendCapable, MotuSendReceiver, GroupChannel):
    ...


class MotuAux(MotuSendReceiver, AuxChannel):
    ...
