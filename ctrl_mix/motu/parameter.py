from __future__ import annotations

from abc import ABC
from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from core.mixer import Parameter, TParam
from ctrl_mix import gain_to_norm, norm_to_gain

if TYPE_CHECKING:
    from motu.channel import MotuMixerChannel


class MotuParameter(Parameter, ABC):
    value_type = type[TParam]
    _to_normalized: Callable | None = None
    _from_normalized: Callable | None = None
    _set_filter: Callable | None = None

    def __init__(self, channel: MotuMixerChannel, path: str) -> None:
        self.channel = channel
        self.param_path = path
        self.path = "/".join([channel.path, path])
        self.name = path.split("/")[-1]
        self._value: TParam
        self._normalized: TParam
        self.default: TParam

    @classmethod
    def create(cls, channel: MotuMixerChannel, path: str, mix_state: dict[str, Any]):
        cfg_type, default, min_val, max_val, unit = cls.read_config(path, mix_state)

        p_types = {"bool": BoolParam, "real": FloatParam}
        p_cls = p_types.get(cfg_type)

        assert p_cls is not None, "Unhandled parameter type"

        p_name = path.split("/")[-1]

        if issubclass(p_cls, FloatParam):
            if p_name in ("fader", "send"):
                instance = VolumeParam(channel, path, default, min_val, max_val)
            else:
                instance = FloatParam(channel, path, default, min_val, max_val)
        else:
            instance = p_cls(channel, path, default)

        return instance

    def __repr__(self) -> str:
        return f"Parameter({self.path} = {self._value})"

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value: TParam):
        self._value = new_value
        self._normalized = new_value

        if self._to_normalized:
            self._normalized = self._to_normalized(new_value)

        self.channel.mixer._on_parameter_set(self)

    @property
    def normalized(self):
        return self._normalized

    @normalized.setter
    def normalized(self, new_value: TParam):
        self._normalized = new_value
        self._value = new_value

        if self._from_normalized:
            self._value = self._from_normalized(new_value)

        if self._set_filter:
            self._value = self._set_filter(self._value)

        self.channel.mixer._on_parameter_set(self)

    def parse_config(self, mix: dict[str, TParam]):
        cfg_key = self.param_path
        if cfg_key.endswith("/send"):
            cfg_key = "matrix/fader"
        config = str(mix[f"ctrls/{cfg_key}"])

        match config.split(":"):
            case [cfg_type, default]: ...
            case [cfg_type, default, min_val, max_val, unit]: ...
            case _:
                cfg_type, default = "real", "0"
                min_val, max_val, unit = None, None, None

        ptype = {"bool": float, "int": int}.get(cfg_type, float)
        default = ptype(default) if default is not None else ptype()
        self.min_val = ptype(min_val) if min_val is not None else None
        self.max_val = ptype(max_val) if max_val is not None else None
        self.unit = unit

        return ptype, default

    @staticmethod
    def read_config(path: str, mix: dict[str, Any]):
        if path.endswith("/send"):
            path = "matrix/fader"

        min_val, max_val, unit = None, None, None
        match str(mix[f"ctrls/{path}"]).split(":"):
            case [cfg_type, default]: ...
            case [cfg_type, default, min_val, max_val, unit]: ...
            case _:
                cfg_type, default = "", ""

        default = float(default)
        min_val = min_val if min_val is None else float(min_val)
        max_val = max_val if max_val is None else float(max_val)

        return cfg_type, default, min_val, max_val, unit


class FloatParam(MotuParameter):
    value_type = float

    def __init__(self, channel: MotuMixerChannel, path: str, default: TParam, min_val: TParam | None, max_val: TParam | None) -> None:
        super().__init__(channel, path)
        self.default = float(default)
        self.value = self.default
        self.min_val = None if min_val is None else float(min_val)
        self.max_val = None if max_val is None else float(max_val)

    def _before_set_filter(self, new_value: float):
        if self.min_val is not None:
            new_value = max(self.min_val, new_value)

        if self.max_val is not None:
            new_value = min(self.max_val, new_value)

        return new_value


class VolumeParam(FloatParam):
    def _to_normalized(self, value): return gain_to_norm(value)
    def _from_normalized(self, value): return norm_to_gain(value)


class BoolParam(MotuParameter):
    value_type = bool

    @staticmethod
    def _to_normalized(new_value):
        return new_value > 0.5

    @staticmethod
    def _from_normalized(new_value):
        return 1.0 if new_value else 0.0

    def __init__(self, channel: MotuMixerChannel, path: str, default: TParam) -> None:
        super().__init__(channel, path)

        self.default = float(default)
        self.value = self.default
