import threading
from typing import Any
import requests
import time
import json
from threading import Thread
import asyncio


type T_Store = int | float | str


def remap(t, a_min, a_max, b_min, b_max, clamp=True):
    a_range, b_range = a_max - a_min, b_max - b_min
    remapped = (t - a_min) * b_range / a_range + b_min

    if clamp:
        return min(max(remapped, b_min), b_max)

    return remapped


class MotuClient:
    def __init__(self, device_id: str, client_id: int | None = None, request_rate=0.025) -> None:
        self.device_id = device_id
        self.client_id = client_id
        self.api_url = f'http://localhost:1280/{device_id}/datastore/mix'
        self.api_url += f'?client_id={client_id}' if client_id else ''
        self.request_rate = request_rate
        self.store: dict[str, T_Store] = {}
        self.patch: dict[str, T_Store] = {}
        self.lock = threading.Lock()
        self.last_request_time = 0.0
        self.push_scheduled = False

        self.fetch_datastore()

        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()

    def _run_event_loop(self):
        """Run the event loop in a background thread."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def write(self, path: str, value: T_Store):
        self.store[path] = value
        self.patch[path] = value

        if not self.push_scheduled:
            self.push_scheduled = True
            asyncio.run_coroutine_threadsafe(self.schedule_patch(), self.loop)

    async def schedule_patch(self):
        elapsed = time.time() - self.last_request_time
        delay = max(0, self.request_rate - elapsed)

        if delay > 0:
            await asyncio.sleep(delay)

        self.last_request_time = time.time()
        self.push_scheduled = False
        self.commit_patch()

    def commit_patch(self):
        data = {'json': json.dumps(self.patch)}
        self.patch = {}
        requests.post(f"{self.api_url}", data)
        # print(data['json'])

    def fetch_datastore(self):
        try:
            self.store = requests.get(f"{self.api_url}").json()
        except Exception as e:
            print(e)
