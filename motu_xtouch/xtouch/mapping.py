from __future__ import annotations
from dataclasses import dataclass
from mido import Message

from xtouch.control import XTouchControlDescriptor, ControlEventFlags, ControlFlags


@dataclass
class MapRange:
    start: int
    length: int = 8

    def __post_init__(self):
        self.values = range(self.start, self.start + self.length)

    def contains(self, n: int):
        return n in self.values


@dataclass
class MapRanges:
    a_ranges: list[MapRange]
    b_ranges: list[MapRange]
    ctrl_type: ControlFlags
    event: ControlEventFlags = ControlEventFlags(0)

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


class XtouchMapping:
    cc_lookup: dict[int, tuple[XTouchControlDescriptor, MapRanges]] = {}
    note_lookup: dict[int, tuple[XTouchControlDescriptor, MapRanges]] = {}

    _cc_ranges = {
        "encoders": MapRanges(
            [MapRange(10), MapRange(18)],
            [MapRange(37), MapRange(45)],
            ControlFlags.Encoder,
            ControlEventFlags.Move
        ),

        "faders": MapRanges(
            [MapRange(1)],
            [MapRange(28)],
            ControlFlags.Fader,
            ControlEventFlags.Move
        ),

        "faders_touch": MapRanges(
            [MapRange(101)],
            [MapRange(111)],
            ControlFlags.Fader,
            ControlEventFlags.Press
        ),

        "master_fader": MapRanges(
            [MapRange(9, 1)],
            [MapRange(36, 1)],
            ControlFlags.Fader | ControlFlags.Master,
            ControlEventFlags.Move
        ),

        "master_fader_touch": MapRanges(
            [MapRange(109, 1)],
            [MapRange(119, 1)],
            ControlFlags.Fader | ControlFlags.Master,
            ControlEventFlags.Press
        ),
    }

    _note_ranges = {
        "encoders": MapRanges(
            [MapRange(0), MapRange(8)],
            [MapRange(55), MapRange(63)],
            ControlFlags.Encoder,
            ControlEventFlags.Press
        ),

        "buttons": MapRanges(
            [MapRange(16), MapRange(24), MapRange(32), MapRange(40)],
            [MapRange(71), MapRange(79), MapRange(87), MapRange(95)],
            ControlFlags.Button,
            ControlEventFlags.Press
        ),

        "master_button": MapRanges(
            [MapRange(48, 1)],
            [MapRange(103, 1)],
            ControlFlags.Button | ControlFlags.Master,
            ControlEventFlags.Press
        ),

        "transport_buttons": MapRanges(
            [MapRange(49, 6)],
            [MapRange(104, 6)],
            ControlFlags.Button | ControlFlags.Transport,
            ControlEventFlags.Press
        ),
    }

    @staticmethod
    def digest_message(msg: Message) -> tuple[XTouchControlDescriptor | None, ControlEventFlags]:
        descriptor, event = None, ControlEventFlags(0)

        if msg.type == "control_change" and msg.control in XtouchMapping.cc_lookup:
            descriptor, ranges = XtouchMapping.cc_lookup[msg.control]
            event |= ranges.event

            if ranges.event & ControlEventFlags.Press and msg.value > 0:
                event |= ControlEventFlags.Down

        elif msg.type in ['note_on', 'note_off'] and msg.note in XtouchMapping.note_lookup:
            descriptor, ranges = XtouchMapping.note_lookup[msg.note]
            event |= ranges.event

            if msg.type == "note_on":
                event |= ControlEventFlags.Down

        return descriptor, event

    @staticmethod
    def _build_lookups():
        assert XtouchMapping.cc_lookup == {}
        assert XtouchMapping.note_lookup == {}

        XtouchMapping.cc_lookup = XtouchMapping._build_lookup(
            XtouchMapping._cc_ranges)

        XtouchMapping.note_lookup = XtouchMapping._build_lookup(
            XtouchMapping._note_ranges)

    @staticmethod
    def _build_lookup(values: dict[str, MapRanges]) -> dict[int, tuple[XTouchControlDescriptor, MapRanges]]:
        lookup = {}

        for ranges in values.values():
            for layer in ranges.a_ranges, ranges.b_ranges:
                for y, x_range in enumerate(layer):
                    for n in x_range.values:
                        lookup[n] = (
                            XTouchControlDescriptor(
                                int(layer == ranges.b_ranges),
                                y,
                                n - x_range.start,
                                ranges.ctrl_type,
                            ),
                            ranges
                        )

        return lookup


XtouchMapping._build_lookups()
