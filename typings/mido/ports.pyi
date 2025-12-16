from typing import Generator
from . import Message


class BasePort:

    def __init__(self, input: str, output: str): ...
    def __iter__(self) -> Generator[Message]: ...
    def receive(self, block: bool = True) -> Message: ...
    def close(self) -> None: ...
    def iter_pending(self) -> Generator[Message]: ...


class Input(BasePort):
    name: str


class Output(BasePort):
    name: str
    def send(self, message: Message): ...


class IOPort(BasePort):
    name: str

    def send(self, message: Message): ...
