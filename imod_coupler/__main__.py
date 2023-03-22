import os
import sys
import time
from pathlib import Path

import tomli as tomllib
from loguru import logger

from imod_coupler import __version__
from imod_coupler.config import BaseConfig
from imod_coupler.drivers.match_driver import match_driver
from imod_coupler.parser import parse_args
from imod_coupler.utils import setup_logger


def main() -> None:
    args = parse_args()

    if args.enable_debug_native:
        # wait for native debugging
        input(f"PID: {os.getpid()}, press any key to continue ....")

    config_path = Path(args.config_path).resolve()

    try:
        run_coupler(config_path)
    except:
        logger.exception("iMOD Coupler run failed with: ")
        sys.exit(1)


def run_coupler(config_path: Path) -> None:
    with open(config_path, "rb") as f:
        config_dict = tomllib.load(f)

    config_dir = config_path.parent
    config_dict["config_dir"] = config_dir
    base_config = BaseConfig(**config_dict)

    setup_logger(base_config.log_level, config_dir / "imod_coupler.log")
    logger.info(f"iMOD Coupler {__version__}")

    if base_config.timing:
        start = time.perf_counter()

    driver = match_driver(
        base_config.driver_type, config_dir, base_config, config_dict["driver"]
    )
    driver.execute()

    # Report timing
    if base_config.timing:
        driver.report_timing_totals()
        end = time.perf_counter()
        logger.info(f"Total elapsed time: {end-start:0.4f} seconds")


if __name__ == "__main__":
    # execute only if run as a script
    main()
