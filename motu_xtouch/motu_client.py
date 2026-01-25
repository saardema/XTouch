import threading
from typing import Any
import requests
import time
import json
import asyncio

from motu_xtouch import ChannelType, InputBank, MixerChannel, T_Store

DEVICE_ID = "0001f2fffe00be6a"


def remap(t, a_min, a_max, b_min, b_max, clamp=True):
    a_range, b_range = a_max - a_min, b_max - b_min
    remapped = (t - a_min) * b_range / a_range + b_min

    if clamp:
        return min(max(remapped, b_min), b_max)

    return remapped


class MotuClient:
    def __init__(self, request_rate=0.025) -> None:
        self.api_url = f'http://localhost:1280/{DEVICE_ID}/datastore'
        self.request_rate = request_rate
        self.store: dict[str, T_Store] = {}
        self.patch: dict[str, T_Store] = {}
        self.lock = threading.Lock()
        self.last_request_time = 0.0
        self.push_scheduled = False
        self.ready = False
        self.input_banks: dict[int, InputBank] = {}
        self.inputs: dict[str, MixerChannel] = {}
        self.groups: dict[str, MixerChannel] = {}
        self.auxs: dict[str, MixerChannel] = {}

        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_event_loop, daemon=False)

        self.boot()

    def boot(self):
        self.thread.start()
        self.update_mix_state()
        self.input_banks = self._parse_input_banks()
        self.inputs = self._parse_routing()
        self.groups = self._parse_groups()

        self.ready = True

    def update_mix_state(self):
        self.store = self._fetch_path("mix")

    def write(self, path: str, value: T_Store):
        """Schedule mutation of a Motu datastore value"""

        if not path:
            return

        self.store[path] = value
        self.patch[path] = value

        if not self.push_scheduled:
            self.push_scheduled = True
            asyncio.run_coroutine_threadsafe(self._schedule_patch(), self.loop)

    def _run_event_loop(self):
        """Run the event loop in a background thread."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def _schedule_patch(self):
        """
        Commit new value immediately or in the near future
        depending on the request rate limit
        """

        elapsed = time.time() - self.last_request_time
        delay = max(0, self.request_rate - elapsed)

        if delay > 0:
            await asyncio.sleep(delay)

        self.last_request_time = time.time()
        self.push_scheduled = False
        self._commit_patch()

    def _commit_patch(self):
        """
        Write the new value in Motu datastore
        and reset the scheduled changes.
        """

        print(self.patch)

        data = {'json': json.dumps(self.patch)}
        self.patch = {}
        requests.patch(f"{self.api_url}/mix", data)

    def _fetch_path(self, sub_path: str) -> dict[str, Any]:
        sub_path = sub_path.removeprefix("/")

        return requests.get(f"{self.api_url}/{sub_path}").json()

    def _parse_routing(self):
        """
        Parse the patchbay matrix to define
        which inputs go to which mixer channel
        """

        inputs: dict[str, MixerChannel] = {}

        for path, value in self._fetch_path("ext/obank/6").items():
            if not isinstance(value, str) or value == "":
                continue

            nodes: list[str] = path.split("/")
            match nodes:
                case ["ch", ch, "src"]:
                    mix_in_ch = int(ch)
                    bank_idx, bank_ch = (int(d) for d in value.split(":"))
                    chan = self.input_banks[bank_idx].channels[bank_ch]
                    if not chan.is_right_channel:
                        chan.mix_in_idx = mix_in_ch
                        inputs[chan.base_name] = chan

        inputs = dict(sorted(inputs.items(), key=lambda ch: ch[1].mix_in_idx))

        return inputs

    def _parse_groups(self):
        groups: dict[str, MixerChannel] = {}

        for bank in self.input_banks.values():
            if bank.name == 'Mix Group':
                groups = {c.base_name: c for c in bank.channels.values() if not c.is_right_channel}

        return groups

    def _parse_input_banks(self):
        channel_banks: dict[int, InputBank] = {}

        for path, value in self._fetch_path("ext/ibank").items():
            if not value:
                continue

            nodes: list[str] = path.split("/")
            bank_idx = int(nodes.pop(0))
            channel_banks.setdefault(bank_idx, InputBank(bank_idx))
            bank = channel_banks[bank_idx]

            match nodes:
                case ["name"]:
                    bank.name = value
                    if bank.name == "Mix Group":
                        bank.channel_type = ChannelType.Group
                    if bank.name == "Mix Aux":
                        bank.channel_type = ChannelType.Aux

                case ["userCh"]: bank.n_channels = value
                case ["ch", ch, "name" | "defaultName" as prop]:
                    if not isinstance(value, str):
                        continue

                    bank_ch_idx = int(ch)

                    if bank_ch_idx in bank.channels:
                        if prop == "defaultName":
                            continue

                    chan = MixerChannel(value, bank_idx=bank_idx, bank_ch_idx=bank_ch_idx, type=bank.channel_type)
                    bank.channels[bank_ch_idx] = chan

        channel_banks = dict(sorted(channel_banks.items()))

        for bank in self.input_banks.values():
            bank.channels = dict(sorted(bank.channels.items()))

        return channel_banks
