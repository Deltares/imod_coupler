import argparse
import logging
import os
import sys
import time

from imod_coupler.metamod import MetaMod
from imod_coupler import __version__
from imod_coupler.config import Config
from imod_coupler.errors import ConfigError

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--enable-debug-native",
        action="store_true",
        help="stop the script to wait for the native debugger.",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s {version}".format(version=__version__),
    )

    parser.add_argument(
        "--config-path",
        action="store",
        required=True,
        help="specify the path to the configuration file.",
    )

    args = parser.parse_args()
    debug_native = args.enable_debug_native
    config_path = args.config_path

    try:
        config = Config(config_path)
    except ConfigError as e:
        logger.error("Could not parse configuration file")
        logger.error(e)
        sys.exit(1)

    logging.basicConfig(level=config.log_level)

    timing = config.timing
    if timing:
        start = time.perf_counter()

    # wait for native debugging
    if debug_native:
        input(f"PID: {os.getpid()}, press any key to continue ....")

    for exchange in config.exchanges:
        if "modflow6" in exchange["kernels"] and "metaswap" in exchange["kernels"]:
            mf6 = config.kernels["modflow6"]
            msw = config.kernels["metaswap"]

            # Print output to stdout
            mf6.set_int("ISTDOUTTOFILE", 0)

            # Initialize kernels
            mf6.initialize()
            msw.initialize()

            # Create an instance
            metamod = MetaMod(mf6=mf6, msw=msw, timing=timing,)
            # Run the time loop
            start_time, current_time, end_time = metamod.getTimes()

            while current_time < end_time:
                current_time = metamod.update_coupled()
            logger.info("New Simulation terminated normally")

            if timing:
                metamod.report_timing_totals()
                end = time.perf_counter()
                logger.info(f"Total elapsed time: {end-start:0.4f} seconds")


if __name__ == "__main__":
    # execute only if run as a script
    main()
