import time
import signal
import sys
import asyncio


import applescript.tell
from mido import Message

from mapping import ControlType, get_path, get_type, load_cfg
from motu_client import MotuClient
from xtouch_client import EncoderMode, XTouchClient
from motu_xtouch import float_to_midi, midi_to_float

# TODO
# Periodically get M state efficiently (Long-polling with ETag)
# All channel mode (sequential mapping, instead of custom mapping)
# On the fly remapping of channels
# Mapping by the channel name instead of channel number

# DONE
# Get M state on layer switch
# Rotary toggle should only toggle on if value == 0
# Map B channels to favorite M channels
# Get/set mutes
# Monitoring with headphones


def init_from_datastore():
    init_faders()
    init_rotary_display()
    init_rotary_encoders()
    init_mutes()
    init_record_arms()


def get_value(ctrl_type: ControlType, x: int, y: int = 0):
    path = get_path(ctrl_type, x, y)

    return motu.store.get(path)


def init_faders():
    for i in range(9):
        path = get_path(ControlType.Fader, i)
        if path:
            value = float_to_midi(motu.store[path])
            xtouch.set_fader(i, value)


def init_rotary_encoders():
    for i in range(8):
        path = get_path(ControlType.Rotary, i)
        if path:
            value = float_to_midi(motu.store[path])
            xtouch.set_rotary(i, value)

    for i in range(8):
        path = get_path(ControlType.Rotary, i, 1)
        if path:
            value = float_to_midi(motu.store[path])
            xtouch.set_rotary(i, value, 1)


def init_rotary_display():
    for cc in range(8):
        xtouch.set_rotary_mode(cc, EncoderMode.Fan)
        xtouch.set_rotary_mode(cc, EncoderMode.Fan, 1)


def init_mutes():
    for i in range(8):
        path = get_path(ControlType.Button, i, 3)
        if path:
            value = float(motu.store[path])
            xtouch.set_button(i, 3, value == 1)


def init_record_arms():
    for i in range(8):
        path = get_path(ControlType.Button, i, 2)
        if path:
            value = float(motu.store[path])
            xtouch.set_button(i, 2, value == 1)


def handle_message(msg: Message):
    ctrl_type, x, y = get_type(msg)
    path = get_path(ctrl_type, x, y)

    # A/B Layer switch
    if ctrl_type & ControlType.CC and msg.control in (26, 63):
        if msg.control == 26 and msg.value == 2 or msg.control == 63 and msg.value == 3:
            # init_from_datastore()
            init_rotary_display()
        return

    # Update state
    elif ctrl_type & ControlType.Press and msg.note == 48:
        motu.update_mix_state()
        init_from_datastore()

    if not path:
        return

    if ctrl_type & ControlType.CC:
        motu.write(path, midi_to_float(msg.value))

    elif ctrl_type & ControlType.Press:

        # Sends and Aux toggle
        if ctrl_type & ControlType.Rotary:
            motu.write(path, 1 if motu.store[path] == 0 else 0)
            value = float_to_midi(motu.store[path])
            xtouch.set_rotary(x, value, y)

        # Mutes and Record arm toggle
        elif ctrl_type & ControlType.Button:
            motu.write(path, 1 if motu.store[path] == 0 else 0)

        # Transport buttons mapped to Music app
        elif ctrl_type & ControlType.Transport:
            cmd = [
                'back track', 'next track',
                '', '',
                'pause and rewind', 'play'
            ][x]

            if cmd:
                applescript.tell.app("Music", cmd)

    # Releasing a button turns it off,
    # so turn it on after releasing if it's supposed to stay on
    elif ctrl_type & ControlType.Button and motu.store[path] == 1:
        xtouch.set_button(x, y, True)


state = {'current_layer': 'A'}
xtouch = XTouchClient(handle_message)
motu = MotuClient()


def main():
    try:
        while not xtouch.ready or not motu.ready:
            if not xtouch.ready:
                xtouch.connect()
            time.sleep(0.5)

        load_cfg("mapping.toml", motu.mix_map)
        init_from_datastore()
        loop = asyncio.new_event_loop()
        loop.run_forever()

    except KeyboardInterrupt:
        sys.exit()


if __name__ == '__main__':
    main()
