from threading import Thread
import math
import time
import mido
import applescript

import motu
import map

DEVICE_NAME = 'X-TOUCH COMPACT'

current_layer = 'A'
connected = False

# TODO
# Periodically get M state efficiently
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
    for (cc, path) in map.FADER_CC.items():
        value = float_to_midi(motu.datastore[path])
        outport.send(mido.Message('control_change', control=cc, value=value))

def set_rotary_encoders():
    # Set rotary encoders 1-8
    for (cc, path) in map.ROTARY_CC.items():
        value = float_to_midi(motu.datastore[path])
        outport.send(mido.Message('control_change', control=cc, value=value))

    # Set rotary encoders 9-16
    for (cc, path) in map.SIDE_ROTARY_CC.items():
        value = float_to_midi(motu.datastore[path])
        outport.send(mido.Message('control_change', control=cc, value=value))

def set_rotary_display():
    # Display everything as off
    for cc in range(10, 25):
        outport.send(mido.Message('control_change', control=cc, value=0, channel=1))
    
    # Display top rotary knob LEDs as fan because they're sends
    for (cc, path) in map.ROTARY_CC.items():
        outport.send(mido.Message('control_change', control=cc, value=2, channel=1))

    for (cc, path) in map.SIDE_ROTARY_CC.items():
        outport.send(mido.Message('control_change', control=cc, value=2, channel=1))

def set_mutes():
    for (note, path) in map.MUTE_NOTE.items():
        value = motu.datastore[path]
        velocity = 0
        if value == 1: velocity = 127
        outport.send(mido.Message('note_on', note=note, velocity=velocity))

def set_record_arms():
    for (note, path) in map.RECORD_ARM_NOTE.items():
        value = motu.datastore[path]
        velocity = 0
        if value == 1: velocity = 127
        outport.send(mido.Message('note_on', note=note, velocity=velocity))

def midi_to_float(value, linear=False):
    value /= 127
    if not linear: value = math.pow(value, 2.5)
    return value

def float_to_midi(value, linear=False):
    if not linear: value = math.pow(value, 1/2.5)
    value *= 127
    value = round(value)
    if value > 127: value = 127
    return value

def periodic_update():
    while True:
        time.sleep(5)
        if time.time() - motu.time_last_patch > 4:
            motu.fetch_datastore()
            # set_b_from_datastore()
            set_faders()
            set_rotary_encoders()
            # set_rotary_display()
            set_mutes()

# Thread(target=periodic_update).start()

# Connect
while not connected:
    try:
        outport = mido.open_output(DEVICE_NAME)
        inport = mido.open_input(DEVICE_NAME)
        connected = True
        print('Connected to ' + DEVICE_NAME)
        set_b_from_datastore()
    except OSError as e:
        print(e)
        time.sleep(1)

for msg in inport:
    # print(msg)

    # CC
    if msg.type == 'control_change':
        
        # Faders
        if msg.control in map.FADER_CC:
            value = midi_to_float(msg.value)
            path = map.FADER_CC[msg.control]
            motu.patch_datastore(path, value)

        # Top rotary knobs
        elif msg.control in map.ROTARY_CC:
            value = midi_to_float(msg.value)
            path = map.ROTARY_CC[msg.control]
            motu.patch_datastore(path, value)
        
        # Side rotary knobs
        elif msg.control in map.SIDE_ROTARY_CC:
            value = midi_to_float(msg.value)
            path = map.SIDE_ROTARY_CC[msg.control]
            motu.patch_datastore(path, value)

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
        if msg.note in map.ROTARY_NOTE:
            path = map.ROTARY_NOTE[msg.note]
            current_value = motu.datastore[path]
            value = 0
            if current_value == 0: value = 1
            motu.patch_datastore(path, value)
            set_rotary_encoders()
        
        # Aux toggle
        elif msg.note in map.SIDE_ROTARY_NOTE:
            path = map.SIDE_ROTARY_NOTE[msg.note]
            current_value = motu.datastore[path]
            value = 0
            if current_value == 0: value = 1
            motu.patch_datastore(path, value)
            set_rotary_encoders()

        # Mutes toggle
        elif msg.note in map.MUTE_NOTE:
            path = map.MUTE_NOTE[msg.note]
            value = 1 - motu.datastore[path]
            motu.patch_datastore(path, value)

        elif msg.note in map.RECORD_ARM_NOTE:
            path = map.RECORD_ARM_NOTE[msg.note]
            value = 1 - motu.datastore[path]
            motu.patch_datastore(path, value)

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
        if msg.note in map.MUTE_NOTE:
            set_mutes()
        elif msg.note in map.RECORD_ARM_NOTE:
            set_record_arms()
