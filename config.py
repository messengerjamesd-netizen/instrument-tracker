import json
import os
import sys
import hashlib


def get_config_path():
    if getattr(sys, "frozen", False):
        base = os.path.join(os.environ.get("APPDATA", os.path.dirname(sys.executable)),
                            "InstrumentTracker")
        os.makedirs(base, exist_ok=True)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "band_tracker_config.json")


DEFAULT_CONFIG = {
    "theme": "default",
    "font_size": "medium",
    "custom_primary": "#2d6bc4",
    "custom_secondary": "#0a1628",
    "pin_enabled": False,
    "pin_hash": "",
    "instruments_sort_col": 1,
    "instruments_sort_asc": True,
    "students_sort_col": 1,
    "students_sort_asc": True,
}


def load_config():
    path = get_config_path()
    if os.path.exists(path):
        try:
            with open(path) as f:
                data = json.load(f)
            for k, v in DEFAULT_CONFIG.items():
                data.setdefault(k, v)
            return data
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config):
    with open(get_config_path(), "w") as f:
        json.dump(config, f, indent=2)


def hash_pin(pin: str) -> str:
    return hashlib.sha256(f"band_tracker_pin_{pin}".encode()).hexdigest()


def verify_pin(pin: str, stored_hash: str) -> bool:
    return hash_pin(pin) == stored_hash
