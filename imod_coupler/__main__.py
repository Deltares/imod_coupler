import argparse
import logging
import os
import sys
import time

from imod_coupler import __version__
from imod_coupler.config import Config
from imod_coupler.drivers.metamod.metamod import MetaMod
from imod_coupler.errors import ConfigError

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "config_path",
        action="store",
        help="specify the path to the configuration file",
    )

    parser.add_argument(
        "--log-level",
        action="store",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="define log level",
    )

    parser.add_argument(
        "--timing",
        action="store_true",
        help="activate timing (verbosity can be adjusted with the log-level)",
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
    config_path = args.config_path
    logging.basicConfig(level=args.log_level)
    timing = args.timing
    debug_native = args.enable_debug_native

    if timing:
        start = time.perf_counter()

    try:
        config = Config(config_path, timing)
    except ConfigError as e:
        logger.error("Could not parse configuration file")
        logger.error(e)
        sys.exit(1)

    if debug_native:
        # wait for native debugging
        input(f"PID: {os.getpid()}, press any key to continue ....")

    kernels = config.kernels
    for exchange in config.exchanges:
        if "modflow6" in exchange["kernels"] and "metaswap" in exchange["kernels"]:
            mf6 = kernels["modflow6"]
            msw = kernels["metaswap"]

            # Print output to stdout
            mf6.set_int("ISTDOUTTOFILE", 0)

            # Create an instance
            metamod = MetaMod(mf6=mf6, msw=msw, timing=timing)

            # This will initialize and couple the kernels
            metamod.initialize()

            # Run the time loop
            start_time, current_time, end_time = metamod.get_times()
            while current_time < end_time:
                current_time = metamod.update()
            logger.info("New Simulation terminated normally")

            metamod.finalize()

    # Report timing
    if timing:
        total = 0
        for kernel in kernels.values():
            total += kernel.report_timing_totals()
        logger.info(f"Total elapsed time in numerical kernels: {total:0.4f} seconds")

        end = time.perf_counter()
        logger.info(f"Total elapsed time: {end-start:0.4f} seconds")


if __name__ == "__main__":
    # execute only if run as a script
    main()
