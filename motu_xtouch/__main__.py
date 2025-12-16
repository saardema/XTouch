from threading import Thread
import math
import time
import signal
import sys
import asyncio

import mido

import applescript.tell

import mapping
from motu_client import MotuClient

DEVICE_NAME = 'X-TOUCH COMPACT'
CLIENT_ID = "0001f2fffe00be6a"

current_layer = 'A'
connected = False
motu = MotuClient(CLIENT_ID)

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


def set_b_from_datastore():
    set_faders()
    set_rotary_encoders()
    set_rotary_display()
    set_mutes()
    set_record_arms()


def set_faders():
    # Set faders 1-8
    for (cc, path) in mapping.FADER_CC.items():
        value = float_to_midi(motu.store[path])
        outport.send(mido.Message('control_change', control=cc, value=value))


def set_rotary_encoders():
    # Set rotary encoders 1-8
    for (cc, path) in mapping.ROTARY_CC.items():
        value = float_to_midi(motu.store[path])
        outport.send(mido.Message('control_change', control=cc, value=value))

    # Set rotary encoders 9-16
    for (cc, path) in mapping.SIDE_ROTARY_CC.items():
        value = float_to_midi(motu.store[path])
        outport.send(mido.Message('control_change', control=cc, value=value))


def set_rotary_display():
    # Display everything as off
    for cc in range(10, 25):
        outport.send(mido.Message('control_change', control=cc, value=0, channel=1))

    # Display top rotary knob LEDs as fan because they're sends
    for (cc, path) in mapping.ROTARY_CC.items():
        outport.send(mido.Message('control_change', control=cc, value=2, channel=1))

    for (cc, path) in mapping.SIDE_ROTARY_CC.items():
        outport.send(mido.Message('control_change', control=cc, value=2, channel=1))


def set_mutes():
    for (note, path) in mapping.MUTE_NOTE.items():
        value = motu.store[path]
        velocity = 0
        if value == 1:
            velocity = 127
        outport.send(mido.Message('note_on', note=note, velocity=velocity))


def set_record_arms():
    for (note, path) in mapping.RECORD_ARM_NOTE.items():
        value = motu.store[path]
        velocity = 0
        if value == 1:
            velocity = 127
        outport.send(mido.Message('note_on', note=note, velocity=velocity))


def midi_to_float(value: int, db=True):
    if db:
        gain = value / 100
        exp = -8 + gain * 8
        f = 2 ** exp
        f -= 2 ** -8
    else:
        f = value / 127

    return min(max(f, 0), 4)


def float_to_midi(value, db=True):
    if value <= 0:
        return 0

    if db:
        value += 2 ** -8
        exp = math.log2(value)
        gain = 1 - exp / -8
        value = gain * 100
    else:
        value *= 127

    value = int(min(max(value, 0), 127))

    return value


def handle_message(msg):
    global current_layer
    # CC
    if msg.type == 'control_change':

        # Faders
        if msg.control in mapping.FADER_CC:
            value = midi_to_float(msg.value, True)
            path = mapping.FADER_CC[msg.control]
            motu.write(path, value)

        # Top rotary knobs
        elif msg.control in mapping.ROTARY_CC:
            value = midi_to_float(msg.value)
            path = mapping.ROTARY_CC[msg.control]
            motu.write(path, value)

        # Side rotary knobs
        elif msg.control in mapping.SIDE_ROTARY_CC:
            value = midi_to_float(msg.value)
            path = mapping.SIDE_ROTARY_CC[msg.control]
            motu.write(path, value)

        # Layer switch to A
        elif msg.control == 26 and current_layer != 'A':
            current_layer = 'A'
            set_b_from_datastore()

        # Layer switch to B
        elif msg.control == 63 and current_layer != 'B':
            current_layer = 'B'
            set_b_from_datastore()

    # Notes
    elif msg.type == 'note_on':

        # Sends toggle
        if msg.note in mapping.ROTARY_NOTE:
            path = mapping.ROTARY_NOTE[msg.note]
            value = 1 if motu.store[path] == 0 else 0
            motu.write(path, value)
            set_rotary_encoders()

        # Aux toggle
        elif msg.note in mapping.SIDE_ROTARY_NOTE:
            path = mapping.SIDE_ROTARY_NOTE[msg.note]
            value = 1 if motu.store[path] == 0 else 0
            motu.write(path, value)
            set_rotary_encoders()

        # Mutes toggle
        elif msg.note in mapping.MUTE_NOTE:
            path = mapping.MUTE_NOTE[msg.note]
            value = 1 - motu.store[path]
            motu.write(path, value)

        elif msg.note in mapping.RECORD_ARM_NOTE:
            path = mapping.RECORD_ARM_NOTE[msg.note]
            value = 1 - motu.store[path]
            motu.write(path, value)

        # Update state
        elif msg.note == 48:
            motu.fetch_datastore()
            set_b_from_datastore()

        elif msg.note == 49:
            applescript.tell.app("Music", 'back track')

        elif msg.note == 50:
            applescript.tell.app("Music", 'next track')

        elif msg.note == 53:
            applescript.tell.app("Music", 'pause and rewind')

        elif msg.note == 54:
            applescript.tell.app("Music", 'play')

    # Update button after lifting
    elif msg.type == 'note_off':
        if msg.note in mapping.MUTE_NOTE:
            set_mutes()
        elif msg.note in mapping.RECORD_ARM_NOTE:
            set_record_arms()


def signal_term_handler(signal, frame):
    print('got SIGTERM')
    sys.exit(0)


def main():
    signal.signal(signal.SIGTERM, signal_term_handler)

    global outport, inport, connected
    while not connected:
        try:
            outport = mido.open_output(DEVICE_NAME)
            inport = mido.open_input(DEVICE_NAME, callback=handle_message)
            connected = True
            print('Connected to ' + DEVICE_NAME)
        except OSError as e:
            print(e)
            time.sleep(1)

    set_b_from_datastore()
    loop = asyncio.new_event_loop()
    loop.run_forever()


if __name__ == '__main__':
    main()
