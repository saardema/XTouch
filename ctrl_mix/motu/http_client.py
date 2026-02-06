from collections.abc import Callable
from random import randint
import threading
from typing import Any
import requests
import time
import json
import asyncio

from core.mixer import TParam


DEVICE_ID = "0001f2fffe00be6a"


class MotuHttpClient:
    def __init__(self, long_poll_callback: Callable[[dict], None], event_loop, request_rate=0.025) -> None:
        self.client_id = randint(0, (1 << 32) - 1)
        self.api_url_base = f'http://localhost:1280/{DEVICE_ID}/datastore'
        self.request_rate = request_rate
        self.long_poll_callback = long_poll_callback
        self.patch: dict[str, TParam] = {}
        self.last_request_time = 0.0
        self.push_scheduled = False
        self.etag = 0

        # self.req_loop = asyncio.new_event_loop()
        self.req_loop = event_loop
        self.req_thread = threading.Thread(target=self._run_req_event_loop)
        self.req_thread.start()

        self.lp_thread = threading.Thread(target=self.long_poll)

    def start_long_poll(self):
        self.lp_thread.start()

    def get_url(self, sub_path: str = ""):
        url = self.api_url_base
        if sub_path:
            url += f"/{sub_path}"
        url += f"?client={self.client_id}"

        return url

    def fetch_path(self, sub_path: str) -> dict[str, TParam]:
        resp = requests.get(self.get_url(sub_path))
        self.etag = int(resp.headers["etag"])

        return resp.json()

    def push_change(self, path: str, value: TParam):
        """
        Schedule mutation of a Motu datastore value.
        Requests are rate limited with eventual consistency.
        """
        self.patch[path] = value

        if not self.push_scheduled:
            self.push_scheduled = True
            asyncio.run_coroutine_threadsafe(self._schedule_patch(), self.req_loop)

    def _run_req_event_loop(self):
        """ Run the event loop in a background thread """

        asyncio.set_event_loop(self.req_loop)
        self.req_loop.run_forever()

    async def _schedule_patch(self):
        """
        Commit new value immediately or in the near future
        depending on the last request time
        """

        elapsed = time.time() - self.last_request_time
        delay = max(0, self.request_rate - elapsed)

        if delay > 0:
            await asyncio.sleep(delay)

        self.last_request_time = time.time()
        self.push_scheduled = False
        data = self.patch.copy()
        self.patch = {}
        self._patch_request("mix", data)
        # print("SEND     ", data)

    def _patch_request(self, path: str, data: dict[str, Any]):
        """
        Modify values in Motu datastore

        :param path: path from the datastore to the root node of data
        :param data: a flat dict where keys are paths
        """

        if len(data) == 1:
            (sub_path, value), = data.items()
            path = "/".join([path, sub_path])
            data = {"value": value}

        url = self.get_url(path)
        body = {'json': json.dumps(data)}

        # Bump state version to sync with Motu Api
        self.etag += 1

        requests.patch(url, body)

    def long_poll(self, path: str = "mix"):
        while True:
            resp = requests.get(
                self.get_url(path),
                headers={"If-None-Match": str(self.etag)}
            )

            if resp.status_code == 304:
                # Expected time out after 15 seconds
                # meaning no change occured
                continue

            if resp.status_code == 200:
                etag = int(resp.headers["etag"])

                if etag == self.etag:
                    # Origin of change was local
                    time.sleep(0.3)
                    continue

                self.etag = etag

                if len(resp.content):
                    data = resp.json()

                    if len(data) == 1:
                        print("     RECV", data)

                    elif len(data) <= 10:
                        print("     RECV")
                        print(json.dumps(data, indent=4))
                    else:
                        print("     RECV", "(the whole fucking datastore)")

                    self.long_poll_callback(data)

            else:
                raise ValueError("Unhandled long poll status header")
