from ports import IOPort, Input, Output


def open_ioport(name: str, *, virtual: bool = False, callback=None, autoreset=False) -> IOPort: ...
def open_output(name=None, virtual=False, autoreset=False) -> Output: ...
def open_input(name=None, virtual=False, callback=None) -> Input: ...
def get_input_names() -> list[str]: ...
def get_output_names() -> list[str]: ...


class Message:
    def __init__(self, type: str, *args, **kwargs) -> None: ...

    type: str
    channel: int
    note: int
    velocity: int

    # msg.type: control_change
    control: int
    value: int

    # msg.type: pitchwheel
    pitch: int
