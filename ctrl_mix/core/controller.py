from abc import ABC
from dataclasses import dataclass


class Control(ABC):
    value: float = 0.0
