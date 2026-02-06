from math import log10

DB_MIN: float = -40.0  # Floor
DB_MAX: float = 12.0  # Gain of 4
GAIN_BIAS: float = 0.01  # Assigns more resolution around 0dB


def lin_log(v, min_log=20.0, max_log=2e4):
    min_log = log10(min_log)
    max_log = log10(max_log)
    log_v = min_log + v * (max_log - min_log)

    return 10 ** log_v


def log_lin(v, min_log=20.0, max_log=2e4):
    min_log = log10(min_log)
    max_log = log10(max_log)
    log_v = log10(v)

    return (log_v - min_log) / (max_log - min_log)


def gain_to_norm(gain: float) -> float:
    # Dash of epsilon to prevent log10 error
    # gain = max(gain, 0.00001)

    gain += GAIN_BIAS

    # Convert linear gain factor to dB
    currentDb = 20.0 * log10(gain)

    # Map dB range to 0..1 range
    norm: float = (currentDb - DB_MIN) / (DB_MAX - DB_MIN)
    norm = clamp(norm, 0, 1)

    return norm


def norm_to_gain(norm: float) -> float:
    # Map 0...1 to the decibel range
    currentDb: float = norm * (DB_MAX - DB_MIN) + DB_MIN

    # Convert dB to linear gain factor
    gain: float = pow(10.0, currentDb / 20.0)

    gain -= GAIN_BIAS

    # Ensure 0 gain at bottom
    if gain <= 0.0001:
        gain = 0.0

    return gain


def clamp(v, low, high):
    return min(max(v, low), high)


def remap(x, from_min, from_max, to_min, to_max, clamped=True):
    from_range, to_range = from_max - from_min, to_max - to_min
    remapped = (x - from_min) * to_range / from_range + to_min

    if clamped:
        return clamp(remapped, to_min, to_max)

    return remapped
