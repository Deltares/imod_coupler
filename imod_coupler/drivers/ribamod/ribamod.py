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

    # TODO: create mapping of river and drainage name to numpy array: 
    # mf6_active_river: Dict[Str, NDArray[Any]]
    # mf6_passive_river: Dict[Str, NDArray[Any]]
    # mf6_active_drainage: Dict[Str, NDArray[Any]]
    # mf6_passive_drainage: Dict[Str, NDArray[Any]]
    # TODO: let the set_river_stages and get_river_stages use this mapping. 
    # TODO: store the ribasim levels, infiltration and drainage pointers.

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
        # Getting the version from ribasim does not work at the moment
        # https://github.com/Deltares/Ribasim/issues/364

    def couple(self) -> None:
        """Couple Modflow and Ribasim"""

        self.max_iter = self.mf6.max_iter()
        # TODO:

    def update(self) -> None:
        # TODO: Store a copy of the river bottom and the river elevation. The
        # river bottom and drainage elevation should not be fall below these
        # values. Note that the river bottom and the drainage elevation may be
        # update every stress period.
        # 
        # iMOD Python sets MODFLOW 6' time unit to days
        # Ribasim's time unit is always seconds
        ribamod_time_factor = 86400

        # Set the MODFLOW 6 river stage and drainage to value of waterlevel of Ribasim basin
        for key in self.coupling.mf6_active_river_packages:
            ribasim_level = self.ribasim.get_value_ptr("level", key)
            self.mf6.set_river_stages(
                mf6_flowmodel_key=self.coupling.mf6_model,
                mf6_package_key=key,
                new_river_stages=ribasim_level,
            )
        for key in self.coupling.mf6_active_drainage_packages:
            ribasim_level = self.ribasim.get_value_ptr("level", key)
            self.mf6.set_drainage_elevation(
                mf6_flowmodel_key=self.coupling.mf6_model,
                mf6_package_key=key,
                new_drainage_elevation=ribasim_level,
            )

        # One time step in MODFLOW 6
        self.mf6.update()

        ribasim_infiltration = self.ribasim.get_value_ptr("infiltration")
        ribasim_drainage = self.ribasim.get_value_ptr("drainage")
        # Zero the ribasim arrays
        ribasim_infiltration[:] = 0.0
        ribasim_drainage[:] = 0.0
        # Compute MODFLOW 6 river and drain flux
        for key in (self.coupling.mf6_active_drainage_packages + self.coupling.mf6_passive_river_packages):
            river_flux = (
                self.mf6.get_river_drain_flux(
                    self.coupling.mf6_model,
                    key,
                )
                / ribamod_time_factor
            )
            # TODO: aggregation step via matrix multiply.
            ribasim_infiltration += np.where(river_flux > 0, river_flux, 0)
            ribasim_drainage += np.where(river_flux < 0, -river_flux, 0)

        for key in (self.coupling.mf6_active_drainage_packages + self.coupling.mf6_passive_drainage_packages):
            drain_flux = -(
                self.mf6.get_river_drain_flux(
                    self.coupling.mf6_model,
                    key,
                )
                / ribamod_time_factor
            )
            # TODO: aggregation step via matrix multiply.
            ribasim_drainage += drain_flux

        # Update Ribasim until current time of MODFLOW 6
        self.ribasim.update_until(self.mf6.get_current_time() * ribamod_time_factor)

    def finalize(self) -> None:
        self.mf6.finalize()
        self.ribasim.finalize()
        self.ribasim.shutdown_julia()
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
