import json
import os
from typing import Dict, Any

_CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config")

def load_config(filename: str) -> Dict[str, Any]:
    path = os.path.join(_CONFIG_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_mechanics_config() -> Dict[str, Any]:
    return load_config("mechanics_params.json")

def load_irrigation_config() -> Dict[str, Any]:
    return load_config("irrigation_params.json")

_config_cache: Dict[str, Any] = {}

def get_mechanics_config() -> Dict[str, Any]:
    if "mechanics" not in _config_cache:
        _config_cache["mechanics"] = load_mechanics_config()
    return _config_cache["mechanics"]

def get_irrigation_config() -> Dict[str, Any]:
    if "irrigation" not in _config_cache:
        _config_cache["irrigation"] = load_irrigation_config()
    return _config_cache["irrigation"]

def reload_config(name: str) -> Dict[str, Any]:
    if name in _config_cache:
        del _config_cache[name]
    if name == "mechanics":
        return get_mechanics_config()
    elif name == "irrigation":
        return get_irrigation_config()
    return {}
