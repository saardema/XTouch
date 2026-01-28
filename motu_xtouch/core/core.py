from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntFlag, auto


class ControlEventFlags(IntFlag):
    # MIDI message contained no handled input
    Unhandled = 0

    # Fader or encoder changed its value
    Move = auto()

    # Button press/encoder push/fader touch
    # start or end
    Press = auto()

    # Press start
    Down = auto()

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return self.name or self.__name__


@dataclass(frozen=True)
class ControlDescriptor(ABC):
    @abstractmethod
    def __hash__(self) -> int: ...


@dataclass
class Control(ABC):
    descriptor: ControlDescriptor
