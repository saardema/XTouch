from collections.abc import Callable


class EventEmitter:
    def __init__(self) -> None:
        self.callbacks: dict[str, set[Callable]] = {}

    def on(self, evt, fn):
        self.callbacks.setdefault(evt, set())
        self.callbacks[evt].add(fn)

    def emit(self, evt, *args, **kwargs):
        for cb in self.callbacks[evt]:
            cb(*args, **kwargs)
