from dataclasses import dataclass
from typing import Any
from mido import Message
import tomllib

from motu_xtouch import ControlType, ChannelType, MixerChannel


@dataclass
class FaderMap:
    mix_in_idx: int = 0
    type: ChannelType = ChannelType.Input

    def get_path(self, control="fader"):
        if self.type is ChannelType.Disabled:
            return ""

        root = "chan"

        if self.type is ChannelType.Master:
            root = "main"
        elif self.type is ChannelType.Aux:
            root = "aux"
        elif self.type is ChannelType.Group:
            root = "group"

        return f"{root}/{self.mix_in_idx}/matrix/{control}"


@dataclass
class MapRange:
    start: int
    length: int = 8


@dataclass
class MapRanges:
    a_ranges: list[MapRange]
    b_ranges: list[MapRange]


fader_map: dict[int, FaderMap] = {}
AUX = [6, 8]


SIDE_ROTARY_MAP = {
    2: 'aux/5/matrix/fader',      # FX send
    3: 'monitor/0/matrix/fader',  # Headphones
    4: 'aux/6/matrix/fader',      # Record
    5: 'aux/2/matrix/fader',      # JBL
    6: 'group/0/matrix/fader',    # Inputs
    7: 'aux/4/matrix/fader',      # Sub
}


FADERS = MapRanges(
    [MapRange(1)],
    [MapRange(28)])

MASTER_FADER = MapRanges(
    [MapRange(9, 1)],
    [MapRange(36, 1)])

MASTER_BUTTON = MapRanges(
    [MapRange(48, 1)],
    [MapRange(103, 1)])

TRANSPORT_BUTTONS = MapRanges(
    [MapRange(49, 6)],
    [MapRange(104, 6)])

ENCODERS = MapRanges(
    [MapRange(10), MapRange(18)],
    [MapRange(37), MapRange(45)])

BUTTONS = MapRanges(
    [MapRange(16), MapRange(24), MapRange(32), MapRange(40)],
    [MapRange(71), MapRange(79), MapRange(87), MapRange(95)])


def get_type(msg: Message) -> tuple[ControlType, int, int]:
    control_type = ControlType.Invalid
    is_cc = msg.type == 'control_change'
    ctrl_nr = msg.control if is_cc else msg.note
    x, y = 0, 0

    if is_cc:
        if is_fader(msg.control):
            control_type |= ControlType.Fader
            x = msg.control - 1
    else:
        if is_button(msg.note):
            control_type |= ControlType.Button

            btn_nr = msg.note - 16
            x = btn_nr % 8
            y = btn_nr // 8

        if is_transport(msg.note):
            control_type |= ControlType.Transport
            x = msg.note - 49

        if msg.type == 'note_on':
            control_type |= ControlType.Press
        elif msg.type == 'note_off':
            control_type |= ControlType.Release

    if is_top_rotary(ctrl_nr, is_cc):
        control_type |= ControlType.Rotary
        x = msg.control - 10 if is_cc else msg.note

    if is_side_rotary(ctrl_nr, is_cc):
        control_type |= ControlType.Rotary
        x = msg.control - 18 if is_cc else msg.note - 8
        y = 1

    if is_cc:
        control_type |= ControlType.CC

    return control_type, x, y


def is_transport(note: int):
    return 49 <= note <= 54


def is_fader(cc: int):
    return 1 <= cc <= 9


def is_side_rotary(n, is_cc=True):
    if is_cc:
        return 18 <= n <= 25

    return 8 <= n <= 15


def is_top_rotary(n, is_cc=True):
    if is_cc:
        return 10 <= n <= 17

    return 0 <= n <= 7


def is_button(note):
    return 16 <= note <= 48


def get_cc(i: int, is_fader=True):
    if is_fader:
        return i + 1
    return i + 10


def get_fader_path(x: int):
    if x in fader_map:
        return fader_map[x].get_path()

    return ""


def get_rotary_path(x: int, y: int = 0):
    if y == 1:
        return SIDE_ROTARY_MAP.get(x, "")

    if x in fader_map:
        return fader_map[x].get_path(f"aux/{AUX[0]}/send")

    return ""


def get_button_path(x: int, y: int = 0):
    if y == 3:
        return fader_map[x].get_path("mute")

    if y < len(AUX):
        return fader_map[x].get_path(f"aux/{AUX[y]}/send")

    return ""


def get_path(ctrl_type: ControlType, x: int, y: int = 0):
    if ctrl_type & ControlType.Fader:
        return get_fader_path(x)

    if ctrl_type & ControlType.Rotary:
        return get_rotary_path(x, y)

    if ctrl_type & ControlType.Button:
        return get_button_path(x, y)

    return ""


def load_cfg(cfg_file_path: str, mix_map: dict[str, MixerChannel] = {}):
    with open(cfg_file_path, "rb") as file:
        mapping_cfg = tomllib.load(file)

    for idx, fader in mapping_cfg["faders"].items():
        fm = FaderMap(type=ChannelType.Input)
        fader_map[int(idx)] = fm

        if fader.get('type') == "Master":
            fm.type = ChannelType.Master

        elif (name := fader.get("name")) and (chan := mix_map.get(name)):
            fm.mix_in_idx = chan.mix_in_idx
