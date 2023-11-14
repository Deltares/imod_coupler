""" Ribamod: the coupling between MetaSWAP and MODFLOW 6

description:

"""
from __future__ import annotations

from collections import ChainMap
from typing import Any, Dict

import numpy as np
from loguru import logger
from numpy.typing import NDArray
from ribasim_api import RibasimApi
from scipy.sparse import csr_matrix

from imod_coupler.config import BaseConfig
from imod_coupler.drivers.driver import Driver
from imod_coupler.drivers.ribametamod.config import Coupling, RibaMetaModConfig
from imod_coupler.kernelwrappers.mf6_wrapper import Mf6Drainage, Mf6River, Mf6Wrapper
from imod_coupler.kernelwrappers.msw_wrapper import MswWrapper
from imod_coupler.logging.exchange_collector import ExchangeCollector


class RibaMetaMod(Driver):
    """The driver coupling Ribasim, MetaSWAP and MODFLOW 6"""

    base_config: BaseConfig  # the parsed information from the configuration file
    ribametamod_config: RibaMetaModConfig  # the parsed information from the configuration file specific to Ribametamod
    coupling: Coupling  # the coupling information

    timing: bool  # true, when timing is enabled
    mf6: Mf6Wrapper  # the MODFLOW 6 kernel
    ribasim: RibasimApi  # the Ribasim kernel
    msw: MswWrapper  # the MetaSWAP XMI kernel

    max_iter: NDArray[Any]  # max. nr outer iterations in MODFLOW kernel
    delt: float  # time step from MODFLOW 6 (leading)

    mf6_head: NDArray[Any]  # the hydraulic head array in the coupled model
    mf6_recharge: NDArray[Any]  # the coupled recharge array from the RCH package
    mf6_storage: NDArray[Any]  # the specific storage array (ss)
    mf6_has_sc1: bool  # when true, specific storage in mf6 is given as a storage coefficient (sc1)
    mf6_area: NDArray[Any]  # cell area (size:nodes)
    mf6_top: NDArray[Any]  # top of cell (size:nodes)
    mf6_bot: NDArray[Any]  # bottom of cell (size:nodes)

    mf6_active_river_packages: Dict[str, Mf6River]
    mf6_passive_river_packages: Dict[str, Mf6River]
    mf6_active_drainage_packages: Dict[str, Mf6Drainage]
    mf6_passive_drainage_packages: Dict[str, Mf6Drainage]
    # ChainMaps
    mf6_river_packages: ChainMap[str, Mf6River]
    mf6_drainage_packages: ChainMap[str, Mf6Drainage]

    # Ribasim variables
    ribasim_level: NDArray[Any]
    ribasim_infiltration: NDArray[Any]
    ribasim_drainage: NDArray[Any]

    # MetaSWAP variables
    mf6_sprinkling_wells: NDArray[Any]  # the well data for coupled extractions
    msw_head: NDArray[Any]  # internal MetaSWAP groundwater head
    msw_volume: NDArray[Any]  # unsaturated zone flux (as a volume!)
    msw_storage: NDArray[Any]  # MetaSWAP storage coefficients (MODFLOW's sc1)

    # Mapping tables
    # Ribasim-MODFLOW
    map_mod2rib: Dict[str, csr_matrix]
    map_rib2mod: Dict[str, csr_matrix]  # TODO: allow more than 1:N
    # MetaSWAP-MODFLOW
    map_mod2msw: Dict[str, csr_matrix] = {}
    map_msw2mod: Dict[str, csr_matrix] = {}

    # Mask tables
    # MetaSWAP-MODFLOW
    mask_mod2msw: Dict[str, NDArray[Any]] = {}
    mask_msw2mod: Dict[str, NDArray[Any]] = {}

    def __init__(self, base_config: BaseConfig, ribametamod_config: RibaMetaModConfig):
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
        self.msw = MswWrapper(
            lib_path=self.ribametamod_config.kernels.metaswap.dll,
            lib_dependency=self.ribametamod_config.kernels.metaswap.dll_dep_dir,
            working_directory=self.ribametamod_config.kernels.metaswap.work_dir,
            timing=self.base_config.timing,
        )

        # Print output to stdout
        self.mf6.set_int("ISTDOUTTOFILE", 0)
        self.mf6.initialize()
        self.ribasim.init_julia()
        self.ribasim.initialize(
            str(self.ribametamod_config.kernels.ribasim.config_file)
        )
        self.msw.initialize()
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
        logger.info(f"MetaSWAP version: {self.msw.get_version()}")

    def couple(self) -> None:
        """Couple Modflow, MetaSWAP and Ribasim"""

        self.max_iter = self.mf6.max_iter()

        # Get all MODFLOW 6 pointers, relevant for coupling with Ribasim
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

        # Get all MODFLOW 6 pointers, relevant for coupling with MetaSWAP
        self.mf6_recharge = self.mf6.get_recharge(
            self.coupling.mf6_model, self.coupling.mf6_msw_recharge_pkg
        )
        self.mf6_storage = self.mf6.get_storage(self.coupling.mf6_model)
        self.mf6_has_sc1 = self.mf6.has_sc1(self.coupling.mf6_model)
        self.mf6_area = self.mf6.get_area(self.coupling.mf6_model)
        self.mf6_top = self.mf6.get_top(self.coupling.mf6_model)
        self.mf6_bot = self.mf6.get_bot(self.coupling.mf6_model)

        # Get all relevant Ribasim pointers
        self.ribasim_infiltration = self.ribasim.get_value_ptr("infiltration")
        self.ribasim_drainage = self.ribasim.get_value_ptr("drainage")
        self.ribasim_level = self.ribasim.get_value_ptr("level")

        # Get all relevant MetaSWAP pointers
        self.msw_head = self.msw.get_head_ptr()
        self.msw_volume = self.msw.get_volume_ptr()
        self.msw_storage = self.msw.get_storage_ptr()

        # Create mappings
        # MODFLOW 6 - Ribasim
        coupling_tables = ChainMap(
            self.coupling.mf6_active_river_packages,
            self.coupling.mf6_passive_river_packages,
            self.coupling.mf6_active_drainage_packages,
            self.coupling.mf6_passive_drainage_packages,
        )
        packages: ChainMap[str, Any] = ChainMap(
            self.mf6_river_packages, self.mf6_drainage_packages
        )
        n_basin = len(self.ribasim_level)

        self.map_mod2rib = {}
        self.map_rib2mod = {}
        for key, path in coupling_tables.items():
            table = np.loadtxt(path, delimiter="\t", dtype=int, skiprows=1, ndmin=2)
            package = packages[key]
            # Ribasim sorts the basins during initialization.
            row, col = table.T
            data = np.ones_like(row, dtype=float)
            # Many to one
            matrix = csr_matrix((data, (row, col)), shape=(n_basin, package.n_bound))
            self.map_mod2rib[key] = matrix
            # One to many, just transpose
            self.map_rib2mod[key] = matrix.T

        # MODFLOW 6 - MetaSWAP

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
        for key, river in self.mf6_active_river_packages.items():
            # TODO: use specific level after Ribasim can export levels
            river.stage[:] = self.map_rib2mod[key].dot(self.ribasim_level)
        for key, drainage in self.mf6_active_drainage_packages.items():
            # TODO: use specific level after Ribasim can export levels
            drainage.elevation[:] = self.map_rib2mod[key].dot(self.ribasim_level)

        # One time step in MODFLOW 6
        self.mf6.update()

        # Zero the ribasim arrays
        self.ribasim_infiltration[:] = 0.0
        self.ribasim_drainage[:] = 0.0
        # Compute MODFLOW 6 river and drain flux
        for key, river in self.mf6_river_packages.items():
            river_flux = river.get_flux(self.mf6_head)
            ribasim_flux = self.map_mod2rib[key].dot(river_flux) / ribamod_time_factor
            self.ribasim_infiltration += np.where(ribasim_flux > 0, ribasim_flux, 0)
            self.ribasim_drainage += np.where(ribasim_flux < 0, -ribasim_flux, 0)

        for key, drainage in self.mf6_drainage_packages.items():
            drain_flux = drainage.get_flux(self.mf6_head)
            ribasim_flux = self.map_mod2rib[key].dot(drain_flux) / ribamod_time_factor
            self.ribasim_drainage -= ribasim_flux

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
