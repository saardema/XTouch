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
    stereo_twin: AudioChannel | None = None
    is_right_channel: bool = False

    @property
    def name(self):
        name = self.default_name

        if self.assigned_name:
            name = self.assigned_name

        elif self.source:
            name = self.source.name

        if self.stereo_twin:
            name = name.removesuffix(" L").removesuffix(" R")

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
    n_available_channels: int
    channels: dict[int, AudioChannel]

    def __post_init__(self):
        self.update_stereo_pairs()

    @classmethod
    def from_bank_data(cls, bank_data: dict):
        return cls(
            name=bank_data["name"],
            n_available_channels=bank_data["userCh"],
            channels={
                int(c): AudioChannel.from_bank_data(ch_data)
                for c, ch_data in bank_data["ch"].items()
            })

    def update_stereo_pairs(self):
        if self.n_available_channels < 2:
            return

        for idx in range(0, self.n_available_channels, 2):
            left, right = self.channels[idx], self.channels[idx + 1]
            if right.name.endswith(" R"):
                left.stereo_twin = right
                right.stereo_twin = left
                right.is_right_channel = True


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
    def __init__(self):
        self._client = MotuHttpClient(self.long_poll_change)
        self.mix_state = self._client.fetch_path("mix")
        self.input_banks, self.output_banks = self.parse_banks()

        self.banks = {
            "chan": self.output_banks[6].channels,
            "group": self.input_banks[7].channels,
            "aux": self.input_banks[9].channels,
        }

    def push_change(self, path: str, value: TParam):
        if self.mix_state[path] == value:
            return

        self.mix_state[path] = value
        self._client.push_change(path, value)

    def long_poll_change(self, data: dict):
        self.mix_state |= data
        print(data)

    def parse_banks(self) -> tuple[dict[int, InputBank], dict[int, OutputBank]]:
        ins = {
            int(bank_nr): InputBank.from_bank_data(bank_data)
            for bank_nr, bank_data in self.fetch("ext/ibank").items()
        }

        outs = {
            int(bank_nr): OutputBank.from_bank_data(bank_data)
            for bank_nr, bank_data in self.fetch("ext/obank").items()
        }

        for bank in outs.values():
            bank.populate_sources(ins)

        return ins, outs

    def fetch(self, path: str):
        flat_dict = self._client.fetch_path(path)

        return self.to_deep_dict(flat_dict)

    def to_deep_dict(self, flat_source: dict) -> dict[str, Any]:
        store_dict = {}

        for path, value in flat_source.items():
            parts = path.split("/")
            base = store_dict

            for key in parts:
                if key != parts[-1]:
                    base = base.setdefault(key, {})

            # The API has a dict and str value for "ctrls/reverb"
            # so rename one of them to avoid a conflict
            if path == "ctrls/reverb":
                key = 'reverbMeterStripOrder'

            base[key] = value

        return store_dict
