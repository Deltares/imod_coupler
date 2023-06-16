""" Ribamod: the coupling between MetaSWAP and MODFLOW 6

description:

"""
from __future__ import annotations

from typing import Any

import numpy as np
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
    ribamod_config: RibaModConfig  # the parsed information from the configuration file specific to Ribamod
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

    def __init__(self, base_config: BaseConfig, ribamod_config: RibaModConfig):
        """Constructs the `Ribamod` object"""
        self.base_config = base_config
        self.ribamod_config = ribamod_config
        self.coupling = ribamod_config.coupling[
            0
        ]  # Adapt as soon as we have multimodel support

    def initialize(self) -> None:
        self.mf6 = Mf6Wrapper(
            lib_path=self.ribamod_config.kernels.modflow6.dll,
            lib_dependency=self.ribamod_config.kernels.modflow6.dll_dep_dir,
            working_directory=self.ribamod_config.kernels.modflow6.work_dir,
            timing=self.base_config.timing,
        )
        self.ribasim = RibasimApi(
            lib_path=self.ribamod_config.kernels.ribasim.dll,
            lib_dependency=self.ribamod_config.kernels.ribasim.dll_dep_dir,
            timing=self.base_config.timing,
        )
        # Print output to stdout
        self.mf6.set_int("ISTDOUTTOFILE", 0)
        self.mf6.initialize()
        self.ribasim.init_julia()
        self.ribasim.initialize(str(self.ribamod_config.kernels.ribasim.config_file))
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
        # Set the MODFLOW 6 river stage to value of waterlevel of Ribasim basin
        ribasim_level = self.ribasim.get_value_ptr("level")
        mf6_river_stage = self.mf6.get_river_stages(
            self.coupling.mf6_model, self.coupling.mf6_river_pkg
        )
        mf6_river_stage[0] = ribasim_level[0]  # TODO: add sparse matrix mapping

        # One time step in MODFLOW 6
        self.mf6.update()

        # Compute MODFLOW 6 river budget
        river_drain_flux = self.mf6.get_river_drain_flux(
            self.coupling.mf6_model, self.coupling.mf6_river_pkg
        )
        mf6_infiltration = np.where(river_drain_flux > 0, river_drain_flux, 0)
        mf6_drainage = np.where(river_drain_flux < 0, river_drain_flux, 0)

        # Set Ribasim infiltration/drainage terms to value of river budget of MODFLOW 6
        ribasim_infiltration = self.ribasim.get_value_ptr("infiltration")
        ribasim_drainage = self.ribasim.get_value_ptr("drainage")
        ribasim_infiltration[0] = mf6_infiltration[0]  # TODO: add sparse matrix mapping
        ribasim_drainage[0] = mf6_drainage[0]  # TODO: add sparse matrix mapping

        # Update Ribasim until current time of MODFLOW 6
        self.ribasim.update_until(self.mf6.get_current_time())

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
