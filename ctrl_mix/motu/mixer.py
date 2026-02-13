from typing import TypeVar


from core.mixer import Mixer, Parameter, TParam
from ctrl_mix.core.events import EventEmitter
from motu.store import AudioChannel, MixerStore
from ctrl_mix.motu.channel import MotuAux, MotuGroup, MotuInput, \
    MotuMain, MotuMixerChannel, MotuMonitor

T = TypeVar("T", int, str, float, bool)


class MotuMixer(Mixer, EventEmitter):

    def __init__(self, event_loop) -> None:
        self.params: dict[str, Parameter] = {}

        self.store = MixerStore(event_loop)
        self.store.on(MixerStore.StoreUpdated, self._on_store_updated)

        self.input_bank = self.store.get_bank("Mix In")
        self.group_bank = self.store.get_bank("Mix Group")
        self.aux_bank = self.store.get_bank("Mix Aux")

        super().__init__(len(self.input_bank), len(self.group_bank), len(self.aux_bank))

        self.main = MotuMain(self, 0, "Main")
        self.monitor = MotuMonitor(self, 0, "Monitor")

        self.channels: dict[int, MotuInput] = {
            i: MotuInput(self, i, chan.name)
            for i, chan in self.input_bank.items()
        }

        self.groups: dict[int, MotuGroup] = {
            i: MotuGroup(self, i, chan.name)
            for i, chan in self.group_bank.items()
        }

        self.aux: dict[int, MotuAux] = {
            i: MotuAux(self, i, chan.name)
            for i, chan in self.aux_bank.items()
        }

        self.init_params()

    def init_params(self):
        self.main.init_params(self.store.mix_state_deep["main"]["0"])
        self.monitor.init_params(self.store.mix_state_deep["monitor"]["0"])

        for i, chan in self.channels.items():
            chan.init_params(self.store.mix_state_deep["chan"][str(i)])

        for i, chan in self.groups.items():
            chan.init_params(self.store.mix_state_deep["group"][str(i)])

        for i, chan in self.aux.items():
            chan.init_params(self.store.mix_state_deep["aux"][str(i)])

    def emit_parameters(self):
        for path, param in self.params.items():
            if self.store.mix_state.get(path):
                self.emit(self.ParameterSetFromMixer, param)

    def set_parameter(self, param: Parameter, ctrl_value: float):
        if param.normalized != ctrl_value:
            param.normalized = ctrl_value
            self.store.push_change(param.key, param.value)

    def _on_store_updated(self, change: dict[str, TParam]):
        for path in change:
            if param := self.params.get(path):
                self.emit(self.ParameterSetFromMixer, param)

    def _init_bank(self, target: dict, bank: dict[int, AudioChannel], cls: type[MotuMixerChannel]):
        for i, chan in bank.items():
            target[i] = cls(self, i, chan.name)
