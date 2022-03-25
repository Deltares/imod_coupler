import argparse
import logging
import os
import sys
import time
from pathlib import Path

import toml

from imod_coupler import __version__
from imod_coupler.drivers.metamod.metamod import MetaMod

logger = logging.getLogger(__name__)


def try_main() -> None:
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
        version="%(prog)s {version}".format(version=__version__),
    )

    args = parser.parse_args()
    config_path = Path(args.config_path).resolve()
    config = toml.load(config_path)

    # TODO: validate with generic json schema

    logging.basicConfig(level=config["log_level"])

    if config["timing"]:
        start = time.perf_counter()

    if args.enable_debug_native:
        # wait for native debugging
        input(f"PID: {os.getpid()}, press any key to continue ....")

    if config["driver_type"] == "metamod":
        driver = MetaMod(config, config_path)

    # This will initialize and couple the kernels
    driver.initialize()

    # Run the time loop
    start_time, current_time, end_time = driver.get_times()
    while current_time < end_time:
        current_time = driver.update()
    logger.info("New simulation terminated normally")

    driver.finalize()

    # Report timing
    if config["timing"]:
        driver.report_timing_totals()
        end = time.perf_counter()
        logger.info(f"Total elapsed time: {end-start:0.4f} seconds")


def main() -> None:
    try:
        try_main()
    except:
        logging.exception("iMOD Coupler run failed with: ")
        sys.exit(1)


if __name__ == "__main__":
    # execute only if run as a script
    main()
