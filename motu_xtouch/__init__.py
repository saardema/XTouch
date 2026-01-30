import math

DB_MIN: float = -48.0  # Floor
DB_MAX: float = 12.0  # Gain of 4
GAIN_BIAS: float = 0.003  # Linearization


def gain_to_norm(gain: float) -> float:
    # Dash of epsilon to prevent log10 error
    # gain = max(gain, 0.00001)

    gain += GAIN_BIAS

    # Convert linear gain factor to dB
    currentDb = 20.0 * math.log10(gain)

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
    if gain <= 0.001:
        gain = 0.0

    return gain


def remap(t, a_min, a_max, b_min, b_max, clamp=True):
    a_range, b_range = a_max - a_min, b_max - b_min
    remapped = (t - a_min) * b_range / a_range + b_min

    if clamp:
        return min(max(remapped, b_min), b_max)

    return remapped


def clamp(v, low, high):
    return min(max(v, low), high)
