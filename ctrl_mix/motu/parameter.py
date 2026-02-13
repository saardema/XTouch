from abc import ABC
import re
from typing import TYPE_CHECKING, Any
from core.mixer import ParamConfig, Parameter, TParam
from ctrl_mix import gain_to_norm, lin_log, log_lin, norm_to_gain, remap

if TYPE_CHECKING:
    from motu.channel import MotuMixerChannel


class MotuParameter(Parameter, ABC):
    value_type = type

    def __init__(
            self,
            channel: MotuMixerChannel,
            param_type: type[TParam],
            base_path: str,
            rel_path: str,
            mix_state: dict,
            cfg: ParamConfig,
            is_log: bool = False
    ) -> None:

        self.base_path = base_path
        self.rel_path = rel_path
        full_path = f"{base_path}/{rel_path}"
        name = rel_path.split("/")[-1]

        super().__init__(full_path, param_type, cfg, channel, name)

        self.is_log = is_log
        self._mix_state = mix_state

    def __repr__(self) -> str:
        return f"Parameter({self.rel_path} = {self.value})"

    @property
    def value(self):
        return self._mix_state[self.key]

    @value.setter
    def value(self, value: TParam):
        value = self.cfg.clamp(value)
        self._mix_state[self.key] = value

    @property
    def normalized(self):
        return self._to_normalized(self.value)

    @normalized.setter
    def normalized(self, value: TParam):
        self.value = self._from_normalized(value)

    @classmethod
    def create(cls, channel: MotuMixerChannel, base_path: str, rel_path: str, mix_state: dict[str, Any]):

        p_types: dict[str, tuple[type[MotuParameter], type]] = {
            "bool": (BoolParam, bool),
            "real": (MotuParameter, float),
            "int": (IntParam, int),
            "enum": (IntParam, int),
        }

        cfg = cls.read_config(rel_path, mix_state)
        assert cfg.type in p_types, "Unhandled parameter type"
        param_cls, value_type = p_types[cfg.type]

        if cfg.type == "real" and cfg.unit == "linear":
            param_cls = VolumeParam

        is_log = cfg.unit == "Hz"

        if is_log:
            assert cfg.min is not None and cfg.max is not None, \
                "Logarithmic parameters require a min and max"

        instance = param_cls(channel, value_type, base_path, rel_path, mix_state, cfg, is_log)

        return instance

    @staticmethod
    def read_config(path: str, mix: dict[str, Any]):
        if path.endswith("/send"):
            path = "matrix/fader"
        path = re.sub(r"(aux|group|reverb)/\d+/", "", path)

        cfg_type, default = None, None
        min_val, max_val, unit = None, None, None
        enums = []

        match str(mix[f"ctrls/{path}"]).split(":"):
            case [cfg_type, default]: ...
            case [cfg_type, default, *enums] if cfg_type == "enum": ...
            case [cfg_type, default, min_val, max_val, unit]: ...

        assert cfg_type is not None
        assert default is not None

        if min_val != None:
            min_val = float(min_val)
        if max_val != None:
            max_val = float(max_val)

        return ParamConfig(
            cfg_type, default, enums, unit, min_val, max_val)


class BoolParam(MotuParameter):

    def _to_normalized(self, value):
        return bool(value)

    def _from_normalized(self, value):
        return int(value)


class IntParam(MotuParameter):

    def _to_normalized(self, value):
        if self.is_log:
            value = log_lin(value, self.cfg.min, self.cfg.max)

        return value

    def _from_normalized(self, value):
        if self.is_log:
            value = lin_log(value, self.cfg.min, self.cfg.max)

        return int(value)


class VolumeParam(MotuParameter):
    def _to_normalized(self, value):
        return gain_to_norm(value)

    def _from_normalized(self, value):
        return norm_to_gain(value)
