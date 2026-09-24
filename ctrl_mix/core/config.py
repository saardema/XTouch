from dataclasses import asdict, dataclass
from typing import TypedDict
import toml
from os.path import isfile

_CONFIG_FILE_NAME = "../config.toml"


@dataclass
class ConfigState:
    motu_device_id: str = ""


config = ConfigState()


def init_config():
    global config

    if not isfile(_CONFIG_FILE_NAME):
        with open(_CONFIG_FILE_NAME, "w") as f:
            toml.dump(asdict(config), f)

    with open(_CONFIG_FILE_NAME, "r") as f:
        for k, v in toml.load(f).items():
            if hasattr(config, k):
                setattr(config, k, v)
