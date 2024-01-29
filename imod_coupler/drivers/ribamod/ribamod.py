""" Ribamod: the coupling between MetaSWAP and MODFLOW 6

description:

"""
from __future__ import annotations

from collections import ChainMap
from typing import Any

import numpy as np
from loguru import logger
from numpy.typing import NDArray
from ribasim_api import RibasimApi
from scipy.sparse import csr_matrix

from imod_coupler.config import BaseConfig
from imod_coupler.drivers.driver import Driver
from imod_coupler.drivers.ribamod.config import Coupling, RibaModConfig
from imod_coupler.kernelwrappers.mf6_wrapper import Mf6Drainage, Mf6River, Mf6Wrapper
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

    mf6_active_river_packages: dict[str, Mf6River]
    mf6_passive_river_packages: dict[str, Mf6River]
    mf6_active_drainage_packages: dict[str, Mf6Drainage]
    mf6_passive_drainage_packages: dict[str, Mf6Drainage]
    # ChainMaps
    mf6_river_packages: ChainMap[str, Mf6River]
    mf6_drainage_packages: ChainMap[str, Mf6Drainage]

    # Ribasim variables
    ribasim_level: NDArray[Any]
    ribasim_infiltration: NDArray[Any]
    ribasim_drainage: NDArray[Any]

    # Mapping tables
    map_mod2rib: dict[str, csr_matrix]
    map_rib2mod: dict[str, csr_matrix]  # TODO: allow more than 1:N

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

        # Get all the relevant river and drainage systems from MODFLOW 6
        mf6_flowmodel_key = self.coupling.mf6_model
        self.mf6_head = self.mf6.get_head(mf6_flowmodel_key)
        self.mf6_active_river_packages = self.mf6.get_rivers_packages(
            mf6_flowmodel_key, list(self.coupling.mf6_active_river_packages.keys())
        )
        self.mf6_passive_river_packages = self.mf6.get_rivers_packages(
            mf6_flowmodel_key, list(self.coupling.mf6_passive_river_packages.keys())
        )
        self.mf6_active_drainage_packages = self.mf6.get_drainage_packages(
            mf6_flowmodel_key, list(self.coupling.mf6_active_drainage_packages.keys())
        )
        self.mf6_passive_drainage_packages = self.mf6.get_drainage_packages(
            mf6_flowmodel_key, list(self.coupling.mf6_passive_drainage_packages.keys())
        )
        self.mf6_river_packages = ChainMap(
            self.mf6_active_river_packages, self.mf6_passive_river_packages
        )
        self.mf6_drainage_packages = ChainMap(
            self.mf6_active_drainage_packages, self.mf6_passive_drainage_packages
        )

        # Get the level, drainage, infiltration from Ribasim
        self.ribasim_infiltration = self.ribasim.get_value_ptr("infiltration")
        self.ribasim_drainage = self.ribasim.get_value_ptr("drainage")
        self.ribasim_level = self.ribasim.get_value_ptr("level")
        self.subgrid_level = self.ribasim.get_value_ptr("subgrid_level")

        # Create mappings
        packages: ChainMap[str, Any] = ChainMap(
            self.mf6_river_packages, self.mf6_drainage_packages
        )
        n_basin = len(self.ribasim_level)
        n_subgrid = len(self.subgrid_level)
        self.map_mod2rib = {}
        self.map_rib2mod = {}
        self.mask_mod2rib = {}
        self.mask_rib2mod = {}

        # Ribasim levels are used to set the boundaries of the "actively" coupled packages.
        # For "passive" packages, Ribasim only collects the net drainage and infiltration.
        active_tables = ChainMap(
            self.coupling.mf6_active_river_packages,
            self.coupling.mf6_active_drainage_packages,
        )
        for key, path in active_tables.items():
            table = np.loadtxt(path, delimiter="\t", dtype=int, skiprows=1, ndmin=2)
            package = packages[key]
            basin_index, bound_index, subgrid_index = table.T
            data = np.ones_like(basin_index, dtype=np.float64)

            mod2rib = csr_matrix(
                (data, (basin_index, bound_index)), shape=(n_basin, package.n_bound)
            )
            rib2mod = csr_matrix(
                (data, (bound_index, subgrid_index)), shape=(package.n_bound, n_subgrid)
            )

            self.map_mod2rib[key] = mod2rib
            self.mask_mod2rib[key] = (mod2rib.getnnz(axis=1) == 0).astype(int)
            self.map_rib2mod[key] = rib2mod
            self.mask_rib2mod[key] = (rib2mod.getnnz(axis=1) == 0).astype(int)

        passive_tables = ChainMap(
            self.coupling.mf6_passive_river_packages,
            self.coupling.mf6_passive_drainage_packages,
        )
        for key, path in passive_tables.items():
            table = np.loadtxt(path, delimiter="\t", dtype=int, skiprows=1, ndmin=2)
            package = packages[key]
            basin_index, bound_index = table.T
            data = np.ones_like(basin_index, dtype=np.float64)
            mod2rib = csr_matrix(
                (data, (basin_index, bound_index)), shape=(n_basin, package.n_bound)
            )
            self.map_mod2rib[key] = mod2rib
            self.mask_mod2rib[key] = (mod2rib.getnnz(axis=1) == 0).astype(int)

    def update(self) -> None:
        # iMOD Python sets MODFLOW 6' time unit to days
        # Ribasim's time unit is always seconds
        ribamod_time_factor = 86400

        self.ribasim.update_subgrid_level()
        # TODO: figure out whether this is required.
        # Without this, it seems like the stage is all 0.0 (uninitialized, makes sense though).
        self.mf6.prepare_time_step(0.0)
        # Set the MODFLOW 6 river stage and drainage to value of waterlevel of Ribasim basin
        for key, river in self.mf6_active_river_packages.items():
            # TODO: use specific level after Ribasim can export levels
            new_stage = self.mask_rib2mod[key][:] * river.stage[:] + self.map_rib2mod[
                key
            ].dot(self.subgrid_level)
            river.set_stage(new_stage=new_stage)
        for key, drainage in self.mf6_active_drainage_packages.items():
            new_elevation = self.mask_rib2mod[key][:] * drainage.elevation[
                :
            ] + self.map_rib2mod[key].dot(self.subgrid_level)
            drainage.set_elevation(new_elevation=new_elevation)

        # TODO: cannot call update because we need to call prepare_time_step() above.
        # update also calls prepare_time_step so we'd advance too much.
        # One time step in MODFLOW 6
        # convergence loop
        self.mf6.prepare_solve(1)
        for kiter in range(1, self.max_iter + 1):
            has_converged = self.do_iter(1)
            if has_converged:
                logger.debug(f"MF6-Ribasim converged in {kiter} iterations")
                break
        self.mf6.finalize_solve(1)
        self.mf6.finalize_time_step()

        # Zero the ribasim arrays
        self.ribasim_infiltration[:] = 0.0
        self.ribasim_drainage[:] = 0.0
        # Compute MODFLOW 6 river and drain flux
        for key, river in self.mf6_river_packages.items():
            # TODO: figure out what do about non-coupled basins.
            # In the current setup, their infiltration/drainage will be set to 0.0
            # Unlike MODFLOW6, where can keep its own value, that doesn't work here.
            # Pragmatically, we could just introduce NaN or Inf and filter in Ribasim.
            river_flux = river.get_flux(self.mf6_head)
            ribasim_flux = self.map_mod2rib[key].dot(river_flux) / ribamod_time_factor
            self.ribasim_infiltration += np.where(ribasim_flux > 0, ribasim_flux, 0)
            self.ribasim_drainage += np.where(ribasim_flux < 0, -ribasim_flux, 0)

        for key, drainage in self.mf6_drainage_packages.items():
            # TODO: mask non-coupled basins.
            drain_flux = drainage.get_flux(self.mf6_head)
            ribasim_flux = self.map_mod2rib[key].dot(drain_flux) / ribamod_time_factor
            self.ribasim_drainage -= ribasim_flux

        # Update Ribasim until current time of MODFLOW 6
        self.ribasim.update_until(self.mf6.get_current_time() * ribamod_time_factor)

    def do_iter(self, sol_id: int) -> bool:
        """Execute a single iteration"""
        has_converged = self.mf6.solve(sol_id)
        return has_converged

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
