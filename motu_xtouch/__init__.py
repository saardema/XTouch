import math


def remap(t, a_min, a_max, b_min, b_max, clamp=True):
    a_range, b_range = a_max - a_min, b_max - b_min
    remapped = (t - a_min) * b_range / a_range + b_min

    if clamp:
        return min(max(remapped, b_min), b_max)

    return remapped


def lin_to_log(value: float) -> float:
    exp = -8 + value * 8
    f = 2 ** exp
    f -= 2 ** -8
    f = min(max(f, 0), 1)

    return f


def log_to_lin(value: float) -> float:
    value += 2 ** -8
    f = 1 - math.log2(value) / -8

    return f


def midi_to_float(value: int, to_db=True):
    if to_db:
        gain = value / 100
        f = lin_to_log(gain)
    else:
        f = value / 127

    return min(max(f, 0), 4)


def float_to_midi(value, db_to_lin=True):
    if value <= 0:
        return 0

    if db_to_lin:
        value = log_to_lin(value)
        value *= 100
    else:
        value *= 127

    value = int(min(max(value, 0), 127))

    return value
