from abc import ABC, abstractmethod


class Control(ABC):
    value: float = 0.0

    @abstractmethod
    def set_value(self, value: float, sync=True):
        """ Sets the value, updating the controller if sync==True"""

    @abstractmethod
    def sync(self):
        """ Updates the controller to reflect the current value """
