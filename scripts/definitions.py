from pathlib import Path


def get_script_path() -> Path:
    return Path(__file__).resolve().parent


def get_root_path() -> Path:
    return get_script_path().parent


def get_recipes_path() -> Path:
    return get_root_path() / "recipes"


def get_default_selection_config():
    return get_root_path() / "defaults.yml"
