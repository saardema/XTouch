from dataclasses import dataclass
from mido import Message
import tomllib

from motu_xtouch import ControlType, ChannelType, MixerChannel


@dataclass
class ChannelState:
    index: int = 0
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

        return f"{root}/{self.index}/matrix/{control}"


@dataclass
class MapRange:
    start: int
    length: int = 8

    def __post_init__(self):
        self._range = range(self.start, self.start + self.length)

    def contains(self, n: int):
        return n in self._range


@dataclass
class MapRanges:
    a_ranges: list[MapRange]
    b_ranges: list[MapRange]

    def contains(self, n: int):
        return bool(self.locate(n))

    def find(self, x: int = 0, y: int = 0, layer: int = 0):
        ranges = self.a_ranges if layer == 0 else self.b_ranges
        if y < len(ranges) and x < ranges[y].length:
            return ranges[y].start + x

        return None

    def locate(self, n: int) -> tuple[int, int, int] | None:
        for layer, layer_ranges in enumerate([self.a_ranges, self.b_ranges]):
            for y, rng in enumerate(layer_ranges):
                if rng.contains(n):
                    return n - rng.start, y, layer

        return None


DEFAULT_SEND_PATH = "main/0/send"
AUX_MIXES = [6, 8, 10, 12]
GROUPS = [0, 2]
fader_mapping: dict[int, ChannelState] = {}
master_fader_map = ChannelState(0, ChannelType.Master)
map_state = {'selected_send_path': DEFAULT_SEND_PATH}


SIDE_ROTARY_MAP = {
    # 2: 'chan/32/matrix/fader',    # FX return
    3: 'monitor/0/matrix/fader',  # Headphones
    4: 'aux/6/matrix/fader',      # Record
    5: 'aux/2/matrix/fader',      # JBL
    6: 'group/0/matrix/fader',    # Inputs
    7: 'aux/4/matrix/fader',      # Sub
}


CHANNEL_FADERS = MapRanges(
    [MapRange(1)],
    [MapRange(28)])

MASTER_FADER = MapRanges(
    [MapRange(9, 1)],
    # [MapRange(36, 1)])
    [MapRange(9, 1)])

MASTER_BUTTON_NOTE = MapRanges(
    [MapRange(48, 1)],
    [MapRange(103, 1)])

TRANSPORT_BUTTONS = MapRanges(
    [MapRange(49, 6)],
    [MapRange(104, 6)])

ENCODERS_NOTE = MapRanges(
    [MapRange(0), MapRange(8)],
    [MapRange(55), MapRange(63)])

ENCODERS_CC = MapRanges(
    [MapRange(10), MapRange(18)],
    [MapRange(37), MapRange(45)])

BUTTONS = MapRanges(
    [MapRange(16), MapRange(24), MapRange(32), MapRange(40)],
    [MapRange(71), MapRange(79), MapRange(87), MapRange(95)])


def parse_message(msg: Message) -> tuple[ControlType, int, int, int]:

    control_type = ControlType.Invalid
    x, y, layer = 0, 0, 0
    if msg.type not in ['note_on', 'note_off', 'control_change']:
        return control_type, x, y, layer

    n = msg.control if msg.is_cc() else msg.note

    if msg.is_cc():
        control_type |= ControlType.CC

        if (ctrl := MASTER_FADER.locate(msg.control)):
            control_type |= ControlType.Fader | ControlType.Master

        elif (ctrl := CHANNEL_FADERS.locate(msg.control)):
            control_type |= ControlType.Fader

        elif ctrl := ENCODERS_CC.locate(n):
            control_type |= ControlType.Encoder

    else:
        if (ctrl := BUTTONS.locate(n)):
            control_type |= ControlType.Button

        elif ctrl := TRANSPORT_BUTTONS.locate(n):
            control_type |= ControlType.Transport

        elif ctrl := ENCODERS_NOTE.locate(n):
            control_type |= ControlType.Encoder

        if msg.type == 'note_on':
            control_type |= ControlType.Press
        elif msg.type == 'note_off':
            control_type |= ControlType.Release

    if ctrl:
        x, y, layer = ctrl
        if control_type & (ControlType.Fader | ControlType.Button | ControlType.Encoder):
            x += layer * 8
        elif control_type & ControlType.Encoder:
            y = 1 if control_type & ControlType.Side else 0

    return control_type, x, y, layer


def get_fader_path(x: int):
    if x in fader_mapping:
        return fader_mapping[x].get_path()

    return ""


def get_selected_send_path(selected: int):
    # Map top 8 buttons to select Aux, Group or Main send mode
    # A1 A2 ... G1 G2 MAIN
    if selected in range(len(AUX_MIXES)):
        return f"aux/{AUX_MIXES[selected]}/send"

    group_idx = selected - 8 + len(GROUPS)
    if group_idx in range(len(GROUPS)):
        return f"group/{GROUPS[group_idx]}/send"

    return DEFAULT_SEND_PATH


def get_encoder_path(x: int, y: int = 0):
    if y == 1:
        return SIDE_ROTARY_MAP.get(x, "")

    if x in fader_mapping and map_state["selected_send_path"]:
        fader = fader_mapping[x]
        return fader.get_path(map_state["selected_send_path"])

    return ""


def get_button_path(x: int, y: int = 0):
    if x in fader_mapping:
        if y == 3:
            return fader_mapping[x].get_path("mute")

        # if y < len(AUX_MIXES):
        #     return fader_mapping[x].get_path(f"aux/{AUX_MIXES[y]}/send")

    return ""


def get_path(ctrl_type: ControlType, x: int = 0, y: int = 0):
    if ctrl_type & ControlType.Fader:
        if ctrl_type & ControlType.Master:
            return master_fader_map.get_path()

        return get_fader_path(x)

    if ctrl_type & ControlType.Encoder:
        return get_encoder_path(x, y)

    if ctrl_type & ControlType.Button:
        return get_button_path(x, y)

    return ""


def load_cfg(
        cfg_file_path: str,
        inputs: dict[str, MixerChannel],
        groups: dict[str, MixerChannel],
        auxs: dict[str, MixerChannel]):

    with open(cfg_file_path, "rb") as file:
        mapping_cfg = tomllib.load(file)
        faders: dict[str, dict] = mapping_cfg["faders"]

    for idx, fader in faders.items():
        chan_name, chan_type = fader.get("name"), fader.get('type')
        fader_map = ChannelState()

        if chan_type:
            fader_map.type = ChannelType[chan_type]

        if chan_name in groups:
            fader_map.index = groups[chan_name].bank_ch_idx

        elif chan_name in auxs:
            fader_map.index = auxs[chan_name].bank_ch_idx

        elif chan_name in inputs:
            fader_map.index = inputs[chan_name].mix_in_idx

        fader_mapping[int(idx)] = fader_map
