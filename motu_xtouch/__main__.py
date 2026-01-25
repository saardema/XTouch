from dataclasses import dataclass
import time
import sys
import asyncio

import applescript.tell
from mido import Message

from mapping import DEFAULT_SEND_PATH, MASTER_BUTTON_NOTE, ControlType, get_encoder_path, get_path, get_selected_send_path, parse_message, load_cfg, map_state
from motu_client import MotuClient
from xtouch_client import XTouchClient
from motu_xtouch import float_to_midi, midi_to_float

# TODO
# Periodically get M state efficiently (Long-polling with ETag)
# All channel mode (sequential mapping, instead of custom mapping)
# On the fly remapping of channels

# DONE
# Mapping by the channel name instead of channel number
# Get M state on layer switch
# Rotary toggle should only toggle on if value == 0
# Map B channels to favorite M channels
# Get/set mutes
# Monitoring with headphones


def init_from_datastore():
    init_faders()
    init_encoder_display()
    init_encoders()
    init_mutes()
    init_record_arms()


def init_faders():
    for i in range(9):
        ct = ControlType.Fader
        if i == 8:
            ct |= ControlType.Master
        path = get_path(ct, i)

        if path:
            value = float_to_midi(motu.store[path])
            xtouch.set_fader(i, value)


def init_encoders():
    for y in range(2):
        for x in range(16):
            value = 0
            if path := get_path(ControlType.Encoder, x, y):
                value = float_to_midi(motu.store[path])
            xtouch.set_encoder(x, value, y)


def init_encoder_display():
    for cc in range(8):
        xtouch.set_encoder_mode(cc, 0)
        xtouch.set_encoder_mode(cc, 1)


def init_mutes():
    for x in range(16):
        path = get_path(ControlType.Button, x, 3)
        if path:
            xtouch.set_button(x, 3, int(motu.store[path] == 1))


def init_record_arms():
    for i in range(16):
        path = get_path(ControlType.Button, i, 2)
        value = int(motu.store[path] == 1) if path else 0
        xtouch.set_button(i, 2, value)


def is_a_b_switch(ctrl_type: ControlType, msg: Message):
    if ctrl_type & ControlType.CC and msg.control in (26, 63):
        if msg.control == 26 and msg.value == 2:
            return True
        if msg.control == 63 and msg.value == 3:
            return True

    return False


def set_encoder(x: int, y: int):
    if path := get_encoder_path(x, y):
        value = float_to_midi(motu.store[path])
        xtouch.set_encoder(x, value, y)


def handle_message(msg: Message):
    ctrl_type, x, y, layer = parse_message(msg)
    path = get_path(ctrl_type, x, y)

    # A/B Layer switch
    if is_a_b_switch(ctrl_type, msg):
        init_encoder_display()
        return

    # Update state
    elif ctrl_type & ControlType.Press and MASTER_BUTTON_NOTE.contains(msg.note):
        motu.update_mix_state()
        init_from_datastore()

    # if not path:
    #     return

    if path and ctrl_type & ControlType.CC:
        value = midi_to_float(msg.value)
        if ctrl_type & ControlType.Master:
            value = min(1, value)
        motu.write(path, value)

    elif ctrl_type & ControlType.Press:
        # Sends and Aux toggle
        if path and ctrl_type & ControlType.Encoder:
            motu.write(path, 1 if motu.store[path] == 0 else 0)
            value = float_to_midi(motu.store[path])
            xtouch.set_encoder(x, value, y)

        # Aux/Group selectors and Mutes
        elif ctrl_type & ControlType.Button:
            if y == 0:
                new_path = get_selected_send_path(x)
                state["selected_button"] = x

                if new_path in [DEFAULT_SEND_PATH, map_state["selected_send_path"]]:
                    new_path = DEFAULT_SEND_PATH
                    state["selected_button"] = -1

                map_state["selected_send_path"] = new_path

                for i in range(8):
                    if i != state["selected_button"]:
                        xtouch.set_button(i, 0, 0)
                    set_encoder(i, 0)

            elif y == 3:
                # Mutes
                new_value = int(motu.store[path] == 0)
                motu.write(path, new_value)

        # Transport buttons mapped to Music app
        elif ctrl_type & ControlType.Transport:
            cmd = [
                'back track', 'next track',
                '', '',
                'pause and rewind', 'play'
            ][x]

            if cmd:
                applescript.tell.app("Music", cmd)

    # Button release
    elif ctrl_type & ControlType.Button:
        # Releasing a button turns it off,
        # so turn it on after releasing if it's supposed to stay on
        if y == 0:
            if state["selected_button"] != -1:
                xtouch.set_button(x, y, 1)

        elif path and motu.store[path] == 1:
            xtouch.set_button(x, y, 1)


xtouch = XTouchClient(handle_message)
motu = MotuClient()
state = {"selected_button": -1}


def main():
    try:
        while not xtouch.ready or not motu.ready:
            if not xtouch.ready:
                xtouch.connect()
            time.sleep(0.5)

        load_cfg("mapping.toml", motu.inputs, motu.groups, motu.auxs)
        init_from_datastore()
        loop = asyncio.new_event_loop()
        loop.run_forever()

    except KeyboardInterrupt:
        sys.exit()


if __name__ == '__main__':
    main()
