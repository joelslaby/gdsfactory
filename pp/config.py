"""gdsfactory loads a configuration from 3 files, high priority overwrites low priority:

1. A config.yml found in the current working directory (highest priority)
2. ~/.gdsfactory/config.yml specific for the machine
3. the default_config in pp/config.py (lowest priority)

`CONFIG` has all your computer specific paths that we do not care to store
`TECH` has all the useful info that we will store to have reproduceable layouts.

You can access all the config dictionary with `print_config` as well as a particular key

"""

__version__ = "2.4.9"
import json
import logging
import os
import pathlib
import subprocess
import tempfile
from pathlib import Path
from pprint import pprint
from typing import Any, Optional

import numpy as np
from omegaconf import OmegaConf

home = pathlib.Path.home()
cwd = pathlib.Path.cwd()
module_path = pathlib.Path(__file__).parent.absolute()
repo_path = module_path.parent
home_path = pathlib.Path.home() / ".gdsfactory"
diff_path = repo_path / "gds_diff"

cwd_config = cwd / "config.yml"
module_config = module_path / "config.yml"
home_config = home_path / "config.yml"
default_config = pathlib.Path(__file__).parent.absolute() / "config.yml"
layer_path = module_path / "klayout" / "tech" / "layers.lyp"

dirpath_build = pathlib.Path(tempfile.TemporaryDirectory().name)
dirpath_test = pathlib.Path(tempfile.TemporaryDirectory().name)
MAX_NAME_LENGTH = 32


TECH = OmegaConf.load(default_config)


if os.access(home_config, os.R_OK) and home_config.exists():
    TECH_HOME = OmegaConf.load(home_config)
    TECH = OmegaConf.merge(TECH, TECH_HOME)

if os.access(cwd_config, os.R_OK) and cwd_config.exists():
    TECH_CWD = OmegaConf.load(cwd_config)
    TECH = OmegaConf.merge(TECH, TECH_CWD)


TECH.info = {}
TECH.info.version = __version__

try:
    from git import InvalidGitRepositoryError, Repo

    try:
        TECH.info.git_hash = Repo(
            repo_path, search_parent_directories=True
        ).head.object.hexsha
        TECH.git_hash_cwd = Repo(cwd, search_parent_directories=True).head.object.hexsha
    except InvalidGitRepositoryError:
        pass

except ImportError:
    pass


CONFIG = dict(
    config_path=cwd_config.absolute(),
    repo_path=repo_path,
    module_path=module_path,
    gdsdir=module_path / "gds",
    font_path=module_path / "gds" / "alphabet.gds",
    masks_path=repo_path / "mask",
    home=home,
    cwd=cwd,
)

mask_name = "notDefined"

if "mask" in TECH:
    mask_name = TECH.mask.name
    mask_config_directory = cwd
    build_directory = mask_config_directory / "build"
    CONFIG["devices_directory"] = mask_config_directory / "devices"
    CONFIG["mask_gds"] = mask_config_directory / "build" / "mask" / f"{mask_name}.gds"
else:
    dirpath_build.mkdir(exist_ok=True)
    build_directory = dirpath_build
    mask_config_directory = dirpath_build

CONFIG["custom_components"] = TECH.custom_components
CONFIG["gdslib"] = TECH.gdslib or repo_path / "gdslib"
CONFIG["sp"] = CONFIG["gdslib"] / "sp"
CONFIG["gds"] = CONFIG["gdslib"] / "gds"
CONFIG["gdslib_test"] = dirpath_test

CONFIG["build_directory"] = build_directory
CONFIG["gds_directory"] = build_directory / "devices"
CONFIG["cache_doe_directory"] = build_directory / "cache_doe"
CONFIG["doe_directory"] = build_directory / "doe"
CONFIG["mask_directory"] = build_directory / "mask"
CONFIG["mask_gds"] = build_directory / "mask" / (mask_name + ".gds")
CONFIG["mask_config_directory"] = mask_config_directory
CONFIG["samples_path"] = module_path / "samples"
CONFIG["netlists"] = module_path / "samples" / "netlists"
CONFIG["components_path"] = module_path / "components"

if "gds_resources" in CONFIG:
    CONFIG["gds_resources"] = CONFIG["masks_path"] / CONFIG["gds_resources"]

build_directory.mkdir(exist_ok=True)
CONFIG["gds_directory"].mkdir(exist_ok=True)
CONFIG["doe_directory"].mkdir(exist_ok=True)
CONFIG["mask_directory"].mkdir(exist_ok=True)
CONFIG["gdslib_test"].mkdir(exist_ok=True)


logging.basicConfig(
    filename=CONFIG["build_directory"] / "log.log",
    filemode="w",
    format="%(name)s - %(levelname)s - %(message)s",
)
logging.warning("This will get logged to a file")


def print_config(key: Optional[str] = None) -> None:
    """Prints a key for the config or all the keys"""
    if key:
        if TECH.get(key):
            print(TECH[key])
        elif CONFIG.get(key):
            print(CONFIG[key])
        else:
            print(f"`{key}` key not found in {cwd_config}")
    else:
        pprint(CONFIG)
        print(OmegaConf.to_yaml(TECH))


def complex_encoder(z):
    if isinstance(z, pathlib.Path):
        return str(z)
    else:
        type_name = type(z)
        raise TypeError(f"Object {z} of type {type_name} is not serializable")


def write_config(config: Any, json_out_path: Path) -> None:
    """Write config to a JSON file."""
    with open(json_out_path, "w") as f:
        json.dump(config, f, indent=2, sort_keys=True, default=complex_encoder)


def call_if_func(f: Any, **kwargs) -> Any:
    """Calls function if it's a function
    Useful to create objects from functions
    if it's an object it just returns the object
    """
    return f(**kwargs) if callable(f) else f


def get_git_hash():
    """Returns repository git hash."""
    try:
        with open(os.devnull, "w") as shutup:
            return (
                subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=shutup)
                .decode("utf-8")
                .strip("\n")
            )
    except subprocess.CalledProcessError:
        return "not_a_git_repo"


GRID_RESOLUTION = TECH.tech.grid_resolution
GRID_PER_UNIT = TECH.tech.grid_unit / GRID_RESOLUTION
GRID_ROUNDING_RESOLUTION = int(np.log10(GRID_PER_UNIT))
BEND_RADIUS = TECH.routing.optical.bend_radius
TAPER_LENGTH = TECH.routing.optical.taper_length
WG_EXPANDED_WIDTH = TECH.routing.optical.wg_expanded_width


if __name__ == "__main__":
    # print(TECH)
    # print_config("gdslib")
    # print_config()
    # print(CONFIG["git_hash"])
    print(CONFIG["sp"])
    # print(CONFIG)
