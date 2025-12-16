CHANNELS = [8, 9, 10, 12, 14, 14, 14, 16]

FADER_CC = {
    1: 'chan/' + str(CHANNELS[0]) + '/matrix/fader',
    2: 'chan/' + str(CHANNELS[1]) + '/matrix/fader',
    3: 'chan/' + str(CHANNELS[2]) + '/matrix/fader',
    4: 'chan/' + str(CHANNELS[3]) + '/matrix/fader',
    5: 'chan/' + str(CHANNELS[4]) + '/matrix/fader',
    6: 'chan/' + str(CHANNELS[5]) + '/matrix/fader',
    7: 'chan/' + str(CHANNELS[6]) + '/matrix/fader',
    8: 'chan/' + str(CHANNELS[7]) + '/matrix/fader',
    9: 'main/0/matrix/fader',
}

ROTARY_CC = {
    10: 'chan/' + str(CHANNELS[0]) + '/matrix/aux/5/send',
    11: 'chan/' + str(CHANNELS[1]) + '/matrix/aux/5/send',
    12: 'chan/' + str(CHANNELS[2]) + '/matrix/aux/5/send',
    13: 'chan/' + str(CHANNELS[3]) + '/matrix/aux/5/send',
    14: 'chan/' + str(CHANNELS[4]) + '/matrix/aux/5/send',
    15: 'chan/' + str(CHANNELS[5]) + '/matrix/aux/5/send',
    16: 'chan/' + str(CHANNELS[6]) + '/matrix/aux/5/send',
    17: 'chan/' + str(CHANNELS[7]) + '/matrix/aux/5/send',
}

ROTARY_NOTE = {
    0: 'chan/' + str(CHANNELS[0]) + '/matrix/aux/5/send',
    1: 'chan/' + str(CHANNELS[1]) + '/matrix/aux/5/send',
    2: 'chan/' + str(CHANNELS[2]) + '/matrix/aux/5/send',
    3: 'chan/' + str(CHANNELS[3]) + '/matrix/aux/5/send',
    4: 'chan/' + str(CHANNELS[4]) + '/matrix/aux/5/send',
    5: 'chan/' + str(CHANNELS[5]) + '/matrix/aux/5/send',
    6: 'chan/' + str(CHANNELS[6]) + '/matrix/aux/5/send',
    7: 'chan/' + str(CHANNELS[7]) + '/matrix/aux/5/send',
}

RECORD_ARM_NOTE = {
    32: 'chan/' + str(CHANNELS[0]) + '/matrix/aux/6/send',
    33: 'chan/' + str(CHANNELS[1]) + '/matrix/aux/6/send',
    34: 'chan/' + str(CHANNELS[2]) + '/matrix/aux/6/send',
    35: 'chan/' + str(CHANNELS[3]) + '/matrix/aux/6/send',
    36: 'chan/' + str(CHANNELS[4]) + '/matrix/aux/6/send',
    37: 'chan/' + str(CHANNELS[5]) + '/matrix/aux/6/send',
    38: 'chan/' + str(CHANNELS[6]) + '/matrix/aux/6/send',
    39: 'chan/' + str(CHANNELS[7]) + '/matrix/aux/6/send',
}

MUTE_NOTE = {
    40: 'chan/' + str(CHANNELS[0]) + '/matrix/mute',
    41: 'chan/' + str(CHANNELS[1]) + '/matrix/mute',
    42: 'chan/' + str(CHANNELS[2]) + '/matrix/mute',
    43: 'chan/' + str(CHANNELS[3]) + '/matrix/mute',
    44: 'chan/' + str(CHANNELS[4]) + '/matrix/mute',
    45: 'chan/' + str(CHANNELS[5]) + '/matrix/mute',
    46: 'chan/' + str(CHANNELS[6]) + '/matrix/mute',
    47: 'chan/' + str(CHANNELS[7]) + '/matrix/mute',
}

SIDE_ROTARY_CC = {
    21: 'monitor/0/matrix/fader',  # Headphones
    23: 'aux/2/matrix/fader',     # JBL
    25: 'aux/4/matrix/fader',     # Sub
    20: 'aux/5/matrix/fader',     # FX send
    24: 'group/0/matrix/fader',   # Inputs
    22: 'aux/6/matrix/fader',     # Record
}

SIDE_ROTARY_NOTE = {
    11: 'monitor/0/matrix/fader',  # Headphones
    13: 'aux/2/matrix/fader',     # JBL
    15: 'aux/4/matrix/fader',     # Sub
    10: 'aux/5/matrix/fader',     # FX send
    14: 'group/0/matrix/fader',   # Inputs
    12: 'aux/6/matrix/fader',     # Record
}
