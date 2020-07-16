import argparse
import logging
import os
import sys
import time

from imod_coupler.metamod import MetaMod

logger = logging.getLogger(__name__)


# copied from https://stackoverflow.com/a/10551190
class EnvDefault(argparse.Action):
    def __init__(self, envvar, required=True, default=None, **kwargs):
        if not default and envvar:
            if envvar in os.environ:
                default = os.environ[envvar]
        if required and default:
            required = False
        super(EnvDefault, self).__init__(default=default, required=required, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--mf6-dll",
        required=True,
        action=EnvDefault,
        envvar="MF6_DLL",
        help="Specify the path to Modflow6 dll \
            (can also be specified using MF6_DLL environment variable).",
    )
    parser.add_argument(
        "--msw-dll",
        required=True,
        action=EnvDefault,
        envvar="MSW_DLL",
        help="Specify the path to Metaswap dll \
            (can also be specified using MSW_DLL environment variable).",
    )
    parser.add_argument(
        "--mf6-model-dir",
        required=True,
        action=EnvDefault,
        envvar="MF6_MODEL_DIR",
        help="Specify the path to Modflow6 model directory "
        + "(can also be specified using MF6_MODEL_DIR environment variable).",
    )
    parser.add_argument(
        "--msw-model-dir",
        required=True,
        action=EnvDefault,
        envvar="MSW_MODEL_DIR",
        help="Specify the path to Metaswap model directory "
        + "(can also be specified using MSW_MODEL_DIR environment variable).",
    )
    # Remove this argument, as soon as the metaswap dll's are in the right place again
    parser.add_argument(
        "--msw-mpi-dll-dir",
        action=EnvDefault,
        envvar="MSW_MPI_DLL_DIR",
        help="Specify the path containing the Metaswap MPI dlls "
        + "(can also be specified using MSW_MPI_DLL_DIR environment variable).",
    )

    parser.add_argument(
        "--enable-debug-native",
        action="store_true",
        help="Stop the script to wait for the native debugger.",
    )

    parser.add_argument(
        "--log-level",
        action="store",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Define log level.",
    )

    parser.add_argument(
        "--timing",
        action="store_true",
        help="Activates timing. Verbosity can be adjusted with the log-level.",
    )

    args = parser.parse_args()
    logging.basicConfig(level=args.log_level)
    mf6_dll = args.mf6_dll
    msw_dll = args.msw_dll
    mf6_model_dir = args.mf6_model_dir
    msw_model_dir = args.msw_model_dir
    msw_mpi_dll_dir = args.msw_mpi_dll_dir
    debug_native = args.enable_debug_native
    timing = args.timing

    if timing:
        start = time.perf_counter()

    if not os.path.exists(mf6_dll):
        logger.error("MODFLOW6 dll " + mf6_dll + " not found.")
        sys.exit(1)

    if not os.path.exists(msw_dll):
        logger.error("METASWAP dd " + msw_dll + " not found.")
        sys.exit(1)

    if not os.path.isdir(mf6_model_dir):
        logger.error("MODFLOW6 Model path " + mf6_model_dir + " not found.")
        sys.exit(1)

    if not os.path.isdir(msw_model_dir):
        logger.error("MetaSWAP Model path " + msw_model_dir + " not found.")
        sys.exit(1)

    if not os.path.isdir(msw_mpi_dll_dir):
        logger.error("Metaswap MPI dlls " + msw_mpi_dll_dir + " not found.")
        sys.exit(1)

    # wait for native debugging
    if debug_native:
        input(f"PID: {os.getpid()}, press any key to continue ....")

    # Create an instance
    MMinst = MetaMod(
        mf6_modeldir=mf6_model_dir,
        msw_modeldir=msw_model_dir,
        mf6_dll=mf6_dll,
        msw_dll=msw_dll,
        msw_dep=msw_mpi_dll_dir,
        timing=timing,
    )
    # Run the time loop
    start_time, current_time, end_time = MMinst.getTimes()

    while current_time < end_time:
        current_time = MMinst.update_coupled()
    logger.info("New Simulation terminated normally")

    if timing:
        MMinst.report_timing_totals()

    if timing:
        end = time.perf_counter()
        logger.info(f"Total elapsed time: {end-start:0.4f} seconds")


if __name__ == "__main__":
    # execute only if run as a script
    main()
