import logging
import os
import sys
import time
from pathlib import Path

import tomli as tomllib

from imod_coupler.drivers.metamod.metamod import MetaMod
from imod_coupler.parser import parse_args


def main() -> None:
    args = parse_args()

    if args.enable_debug_native:
        # wait for native debugging
        input(f"PID: {os.getpid()}, press any key to continue ....")

    config_path = Path(args.config_path).resolve()

    try:
        run_coupler(config_path)
    except:
        logging.exception("iMOD Coupler run failed with: ")
        sys.exit(1)


def run_coupler(config_path: Path) -> None:
    with open(config_path, "rb") as f:
        config = tomllib.load(f)

    # TODO: validate configuration

    logging.basicConfig(level=config["log_level"])

    if config["timing"]:
        start = time.perf_counter()

    if config["driver_type"] == "metamod":
        driver = MetaMod(config, config_path)
    else:
        raise ValueError(f"Driver type {config['driver_type']} is not supported.")

    driver.execute()

    # Report timing
    if config["timing"]:
        driver.report_timing_totals()
        end = time.perf_counter()
        logging.info(f"Total elapsed time: {end-start:0.4f} seconds")


if __name__ == "__main__":
    # execute only if run as a script
    main()
