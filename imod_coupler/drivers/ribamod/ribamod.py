""" RibaMetaMod: the coupling between MetaSWAP and MODFLOW 6

description:

"""
from __future__ import annotations

from typing import Any

from loguru import logger
from numpy.typing import NDArray
from ribasim_api import RibasimApi

from imod_coupler.config import BaseConfig
from imod_coupler.drivers.driver import Driver
from imod_coupler.drivers.ribamod.config import Coupling, RibaModConfig
from imod_coupler.kernelwrappers.mf6_wrapper import Mf6Wrapper
from imod_coupler.logging.exchange_collector import ExchangeCollector


class RibaMod(Driver):
    """The driver coupling Ribasim and MODFLOW 6"""

    base_config: BaseConfig  # the parsed information from the configuration file
    ribametamod_config: RibaModConfig  # the parsed information from the configuration file specific to RibaMetaMod
    coupling: Coupling  # the coupling information

    timing: bool  # true, when timing is enabled
    mf6: Mf6Wrapper  # the MODFLOW 6 kernel
    ribasim: RibasimApi  # the Ribasim kernel

    max_iter: NDArray[Any]  # max. nr outer iterations in MODFLOW kernel
    delt: float  # time step from MODFLOW 6 (leading)

    mf6_head: NDArray[Any]  # the hydraulic head array in the coupled model
    mf6_recharge: NDArray[Any]  # the coupled recharge array from the RCH package
    mf6_storage: NDArray[Any]  # the specific storage array (ss)
    mf6_has_sc1: bool  # when true, specific storage in mf6 is given as a storage coefficient (sc1)
    mf6_area: NDArray[Any]  # cell area (size:nodes)
    mf6_top: NDArray[Any]  # top of cell (size:nodes)
    mf6_bot: NDArray[Any]  # bottom of cell (size:nodes)

    mf6_sprinkling_wells: NDArray[Any]  # the well data for coupled extractions

    def __init__(self, base_config: BaseConfig, ribametamod_config: RibaModConfig):
        """Constructs the `RibaMetaMod` object"""
        self.base_config = base_config
        self.ribametamod_config = ribametamod_config
        self.coupling = ribametamod_config.coupling[
            0
        ]  # Adapt as soon as we have multimodel support

    def initialize(self) -> None:
        self.mf6 = Mf6Wrapper(
            lib_path=self.ribametamod_config.kernels.modflow6.dll,
            lib_dependency=self.ribametamod_config.kernels.modflow6.dll_dep_dir,
            working_directory=self.ribametamod_config.kernels.modflow6.work_dir,
            timing=self.base_config.timing,
        )
        self.ribasim = RibasimApi(
            lib_path=self.ribametamod_config.kernels.ribasim.dll,
            lib_dependency=self.ribametamod_config.kernels.ribasim.dll_dep_dir,
            timing=self.base_config.timing,
        )
        # Print output to stdout
        self.mf6.set_int("ISTDOUTTOFILE", 0)
        self.mf6.initialize()
        self.ribasim.initialize(self.ribametamod_config.kernels.ribasim.config_file)
        self.log_version()
        if self.coupling.output_config_file is not None:
            self.exchange_logger = ExchangeCollector.from_file(
                self.coupling.output_config_file
            )
        else:
            self.exchange_logger = ExchangeCollector()
        self.couple()

    def log_version(self) -> None:
        logger.info(f"MODFLOW version: {self.mf6.get_version()}")
        logger.info(f"Ribasim version: {self.ribasim.get_version()}")

    def couple(self) -> None:
        """Couple Modflow and Ribasim"""

        self.max_iter = self.mf6.max_iter()
        # TODO:

    def update(self) -> None:
        ribasim_level = self.ribasim.get_value_ptr("level")
        mf6_river_stage = self.mf6.get_river_stages(
            self.coupling.mf6_model, self.coupling.mf6_river_pkg
        )
        # FIXME: In the end there will be more than one modflow river node and ribasim basin node
        # FIXME: sparse matrix mapping
        mf6_river_stage[0] = ribasim_level[0]
        self.mf6.update()
        modflow_river_drain_flux = self.mf6.get_river_drain_flux(
            self.coupling.mf6_model, self.coupling.mf6_river_pkg
        )
        # positive q -> into the groundwater -> from ribasim perspective infiltration
        # split q into two arrays, one which comes from positive entries, one from negative ones
        # in the end both arrays only include zeros or positive numbers
        # FIXME: sparse matrix mapping
        self.ribasim.update_until(self.mf6.get_current_time())

        self.mf6.get_current_time()

    def finalize(self) -> None:
        self.mf6.finalize()
        self.ribasim.finalize()
        self.exchange_logger.finalize()

    def get_current_time(self) -> float:
        return self.mf6.get_current_time()

    def get_end_time(self) -> float:
        return self.mf6.get_end_time()

    def report_timing_totals(self) -> None:
        total_mf6 = self.mf6.report_timing_totals()
        total_ribasim = self.ribasim.report_timing_totals()
        total = total_mf6 + total_ribasim
        logger.info(f"Total elapsed time in numerical kernels: {total:0.4f} seconds")
        logger.info(f"Total elapsed time in numerical kernels: {total:0.4f} seconds")
