from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar


from core.mixer import Mixer, TParam
from ctrl_mix.core.events import Event, EventEmitter
from ctrl_mix.motu.channel import MotuAux, MotuGroup, MotuInput, MotuMain, MotuMixerChannel
from motu.parameter import MotuParameter
from motu.store import AudioChannel, MixerStore

T = TypeVar("T", int, str, float, bool)


class MotuMixer(Mixer, EventEmitter):
    ParameterSetFromMixer = Event[Callable[[MotuParameter], None]]("ParameterSetFromMixer")

    def __init__(self) -> None:
        self.params: dict[str, MotuParameter] = {}

        self.store = MixerStore()
        self.store.on(MixerStore.StoreUpdated, self._on_store_updated)

        self.input_bank = self.store.get_bank("Mix In")
        self.group_bank = self.store.get_bank("Mix Group")
        self.aux_bank = self.store.get_bank("Mix Aux")

        super().__init__(len(self.input_bank), len(self.group_bank), len(self.aux_bank))

        self.main = MotuMain(self, 0, "Main")
        self.main.setup()

        self.channels: dict[int, MotuInput] = {}
        self._init_bank(self.channels, self.input_bank, MotuInput)

        self.groups: dict[int, MotuGroup] = {}
        self._init_bank(self.groups, self.group_bank, MotuGroup)

        self.aux: dict[int, MotuAux] = {}
        self._init_bank(self.aux, self.aux_bank, MotuAux)

        self.init_params()

    def init_params(self):
        self.main.init_params(self.store.mix_state)

        for chan in self.channels.values():
            chan.init_params(self.store.mix_state)

        for chan in self.groups.values():
            chan.init_params(self.store.mix_state)

        for chan in self.aux.values():
            chan.init_params(self.store.mix_state)

    def sync_to_store(self):
        for path, param in self.params.items():
            if (val := self.store.mix_state.get(path)) is not None:
                param.value = val
                self.emit(self.ParameterSetFromMixer, param)

    def set_parameter(self, param: MotuParameter, ctrl_value: float):
        param.normalized = ctrl_value
        self.store.push_change(param.path, param.value)

    def _on_store_updated(self, change: dict[str, TParam]):
        for path in change:
            if param := self.params.get(path):
                if param.value != change[path]:
                    param.value = change[path]
                    self.emit(self.ParameterSetFromMixer, param)

    def _on_parameter_set(self, param: MotuParameter):
        ...

    def _init_bank(self, target: dict, bank: dict[int, AudioChannel], cls: type[MotuMixerChannel]):
        for i, chan in bank.items():
            target[i] = cls(self, i, chan.name)
            target[i].setup()
