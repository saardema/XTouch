import math


def remap(t, a_min, a_max, b_min, b_max, clamp=True):
    a_range, b_range = a_max - a_min, b_max - b_min
    remapped = (t - a_min) * b_range / a_range + b_min

    if clamp:
        return min(max(remapped, b_min), b_max)

    return remapped


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
