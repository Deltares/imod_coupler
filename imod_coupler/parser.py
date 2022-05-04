import argparse
from typing import Any

from imod_coupler import __version__


def parse_args() -> Any:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "config_path",
        action="store",
        help="specify the path to the configuration file",
    )

    parser.add_argument(
        "--enable-debug-native",
        action="store_true",
        help="stop the script to wait for the native debugger",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=__version__
    )

    return parser.parse_args()
