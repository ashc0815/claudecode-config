from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).parent
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def load_yaml(filename: str) -> dict:
    with open(CONFIG_DIR / filename) as f:
        return yaml.safe_load(f)
