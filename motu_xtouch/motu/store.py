from __future__ import annotations
from abc import ABC
from dataclasses import dataclass
from typing import Any

from motu.http_client import MotuHttpClient
from core.mixer import TParam


@dataclass()
class AudioChannel:
    assigned_name: str
    default_name: str
    routing: tuple[int, ...] | None = None
    source: AudioChannel | None = None
    name_override: str = ""

    @property
    def name(self):
        name = self.default_name

        if self.name_override:
            name = self.name_override

        elif self.assigned_name:
            name = self.assigned_name

        elif self.source:
            name = self.source.name

        return name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    @staticmethod
    def from_bank_data(bank_data: dict):
        routing = None
        if ":" in bank_data.get("src", ""):
            routing = tuple(map(int, bank_data["src"].split(":")))

        return AudioChannel(
            bank_data["name"],
            bank_data["defaultName"],
            routing
        )


@dataclass(frozen=True)
class ChannelBank(ABC):
    name: str
    n_enabled_channels: int
    channels: dict[int, AudioChannel]

    @classmethod
    def from_bank_data(cls, bank_data: dict):
        return cls(
            name=bank_data["name"],
            n_enabled_channels=bank_data["userCh"],
            channels={
                int(c): AudioChannel.from_bank_data(ch_data)
                for c, ch_data in bank_data["ch"].items()
            })


@dataclass(frozen=True)
class InputBank(ChannelBank):
    ...


@dataclass(frozen=True)
class OutputBank(ChannelBank):
    def populate_sources(self, input_banks: dict[int, InputBank]):
        for channel in self.channels.values():
            if channel.routing:
                bank_nr, bank_ch = channel.routing
                channel.source = input_banks[bank_nr].channels[bank_ch]


class MixerStore:
    """
    Represents state of the Motu audio interface
        - Read-only view into the available inputs and outputs of the audio interface
        - Read/write access to the state of the mixer
    """

    def __init__(self):

        self._client = MotuHttpClient(self.long_poll_change)
        self.mix_state: dict[str, TParam] = {}
        self.update_mix_state()

        self.input_banks: dict[int, InputBank] = {}
        self.input_banks_dir: dict[str, InputBank] = {}
        self.output_banks: dict[int, OutputBank] = {}
        self.output_banks_dir: dict[str, OutputBank] = {}
        self.parse_banks()

    def update_mix_state(self):
        self.mix_state = self._client.fetch_path("mix")

    def get_bank(self, name: str, join_stereo_pairs=True, enabled_only=True) -> dict[int, AudioChannel]:
        channels: dict[int, AudioChannel] = {}

        bank = self.input_banks_dir.get(name)
        if not bank:
            bank = self.output_banks_dir.get(name)

        assert bank is not None

        for i, chan in bank.channels.items():
            if enabled_only and i == bank.n_enabled_channels:
                break

            if join_stereo_pairs and self.is_right_chan(bank, i):
                left = channels[i - 1]
                left.name_override = left.name.removesuffix(" L")
                continue

            channels[i] = chan

        return channels

    def is_right_chan(self, bank, i):
        if i % 2 == 1:
            if bank.name == "Mix Group":
                return True

            if bank.name == "Mix Aux" and self.mix_state[f"aux/{i}/config/format"] == "2:1":
                return True

            if bank.name == "Mix In" and self.mix_state[f"chan/{i}/config/format"] == "2:1":
                return True

        return False

    def push_change(self, path: str, value: TParam):
        if self.mix_state[path] == value:
            return

        self.mix_state[path] = value
        self._client.push_change(path, value)

    def long_poll_change(self, data: dict):
        self.mix_state |= data
        print(data)

    def parse_banks(self):
        for i, bank_data in self._fetch("ext/ibank").items():
            bank = InputBank.from_bank_data(bank_data)
            self.input_banks[int(i)] = bank
            self.input_banks_dir[bank.name] = bank

        for i, bank_data in self._fetch("ext/obank").items():
            bank = OutputBank.from_bank_data(bank_data)
            self.output_banks[int(i)] = bank
            self.output_banks_dir[bank.name] = bank
            bank.populate_sources(self.input_banks)

    def _fetch(self, path: str):
        flat_dict = self._client.fetch_path(path)

        return self._to_deep_dict(flat_dict)

    def _to_deep_dict(self, flat_source: dict) -> dict[str, Any]:
        store_dict = {}

        for path, value in flat_source.items():
            parts = path.split("/")
            base = store_dict

            for key in parts:
                if key != parts[-1]:
                    base = base.setdefault(key, {})

            # The API has both a dict and str value for "ctrls/reverb"
            # so rename one of them to avoid a conflict
            if path == "ctrls/reverb":
                key = 'reverbMeterStripOrder'

            base[key] = value

        return store_dict
