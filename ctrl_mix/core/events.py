from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar, Any
from collections import defaultdict

T = TypeVar('T', bound=Callable[..., Any])


@dataclass(frozen=True)
class Event(Generic[T]):
    """Type-safe event symbol."""
    name: str

    def __hash__(self):
        return hash(self.name)


class EventEmitter:

    def __init__(self):
        self._listeners: dict[Event, set[Callable]] = defaultdict(set)
        self._events: dict[str, Event] = {}

        super().__init__()

    def _register(self, name: str, signature: type):
        setattr(self, name, Event[signature](name))
        self._events[name] = getattr(self, name)

    def on(self, event: Event[T], callback: T) -> None:
        """Register a type-safe event listener."""
        self._listeners[event].add(callback)

    def off(self, event: Event[T], callback: T) -> None:
        """Unregister an event listener."""
        if callback in self._listeners[event]:
            self._listeners[event].remove(callback)

    def emit(self, event: Event, *args: Any, **kwargs: Any) -> None:
        """Emit an event to all registered listeners."""
        for callback in self._listeners[event]:
            callback(*args, **kwargs)
