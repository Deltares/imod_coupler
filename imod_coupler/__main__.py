import argparse
import logging
import json
import os
import sys
import time

from imod_coupler.metamod import MetaMod
from imod_coupler import __version__

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
        required=False,
        action=EnvDefault,
        envvar="MF6_DLL",
        help="specify the path to Modflow6 dll \
            (can also be specified using MF6_DLL environment variable).",
    )
    parser.add_argument(
        "--msw-dll",
        required=False,
        action=EnvDefault,
        envvar="MSW_DLL",
        help="specify the path to Metaswap dll \
            (can also be specified using MSW_DLL environment variable).",
    )
    parser.add_argument(
        "--mf6-model-dir",
        required=False,
        action=EnvDefault,
        envvar="MF6_MODEL_DIR",
        help="specify the path to Modflow6 model directory "
        + "(can also be specified using MF6_MODEL_DIR environment variable).",
    )
    parser.add_argument(
        "--msw-model-dir",
        required=False,
        action=EnvDefault,
        envvar="MSW_MODEL_DIR",
        help="specify the path to Metaswap model directory "
        + "(can also be specified using MSW_MODEL_DIR environment variable).",
    )
    # Remove this argument, as soon as the metaswap dll's are in the right place again
    parser.add_argument(
        "--msw-mpi-dll-dir",
        action=EnvDefault,
        required=False,
        envvar="MSW_MPI_DLL_DIR",
        help="specify the path containing the Metaswap MPI dlls "
        + "(can also be specified using MSW_MPI_DLL_DIR environment variable).",
    )

    parser.add_argument(
        "--enable-debug-native",
        action="store_true",
        help="stop the script to wait for the native debugger.",
    )

    parser.add_argument(
        "--log-level",
        action="store",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="define log level.",
    )

    parser.add_argument(
        "--config",
        action="store",
        default="",
        help="Provide optional config file in json-format.",
    )

    parser.add_argument(
        "--timing",
        action="store_true",
        help="activates timing, verbosity can be adjusted with the log-level.",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s {version}".format(version=__version__),
    )

    if len(sys.argv) == 1:
        sys.argv.append("--help")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level)
    mf6_dll = args.mf6_dll
    msw_dll = args.msw_dll
    mf6_model_dir = args.mf6_model_dir
    msw_model_dir = args.msw_model_dir
    configfile = args.config
    msw_mpi_dll_dir = args.msw_mpi_dll_dir
    debug_native = args.enable_debug_native
    timing = args.timing

    if timing:
        start = time.perf_counter()

    # wait for native debugging
    if debug_native:
        input(f"PID: {os.getpid()}, press any key to continue ....")

    config_data = \
        {'components': {}, 'dependencies': [], 'parameters': [], 'exchanges': []}
    if msw_dll and msw_model_dir:
        config_data['components']['msw'] = \
            {'engine': 'msw', 'dll': msw_dll, 'wd': msw_model_dir}
    if msw_dll and msw_model_dir:
        config_data['components']['mf6'] = \
            {'engine': 'mf6', 'dll': mf6_dll, 'wd': mf6_model_dir}
    if msw_mpi_dll_dir:
        config_data['dependencies'].append(msw_mpi_dll_dir)

    # Parse config file
    if configfile:
        if os.path.isfile(configfile):
            with open(configfile) as fjs:
                config_data = json.load(fjs)
        else:
            logger.error(f"Config file {configfile} not found.")
            sys.exit(1)

    # Create an instance
    metamod = MetaMod(
        config_data,
        timing=timing
    )
 
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
