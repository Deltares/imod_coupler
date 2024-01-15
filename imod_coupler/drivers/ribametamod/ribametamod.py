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

from imod_coupler.config import BaseConfig
from imod_coupler.drivers.driver import Driver
from imod_coupler.drivers.ribametamod.config import Coupling, RibaMetaModConfig
from imod_coupler.drivers.ribametamod.mapping import SetMapping
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
    msw: MswWrapper  # the MetaSWAP kernel
    has_metaswap: bool  # configured with or without metaswap

    max_iter: NDArray[Any]  # max. nr outer iterations in MODFLOW kernel
    delt: float  # time step from MODFLOW 6 (leading)

    mf6_head: NDArray[Any]  # the hydraulic head array in the coupled model
    mf6_recharge: NDArray[Any]  # the coupled recharge array from the RCH package
    mf6_recharge_nodes: NDArray[Any]  # node selection of rch nodes
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
    ribasim_volume: NDArray[Any]

    # MetaSWAP variables
    mf6_sprinkling_wells: NDArray[Any]  # the well data for coupled extractions
    msw_head: NDArray[Any]  # internal MetaSWAP groundwater head
    msw_volume: NDArray[Any]  # unsaturated zone flux (as a volume!)
    msw_storage: NDArray[Any]  # MetaSWAP storage coefficients (MODFLOW's sc1)
    msw_sprinkling_demand_sec: NDArray[
        Any
    ]  # MetaSWAP sprinkling demand for surface water
    msw_ponding_flux_sec: NDArray[Any]  # MetaSWAP ponding flux to surface water

    # Mapping tables
    mapping: SetMapping  # TODO: Ribasim: allow more than 1:N

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
        if self.ribametamod_config.kernels.ribasim is not None:
            self.ribasim = RibasimApi(
                lib_path=self.ribametamod_config.kernels.ribasim.dll,
                lib_dependency=self.ribametamod_config.kernels.ribasim.dll_dep_dir,
                timing=self.base_config.timing,
            )
            self.has_ribasim = True
        else:
            self.has_ribasim = False

        if self.ribametamod_config.kernels.metaswap is not None:
            self.msw = MswWrapper(
                lib_path=self.ribametamod_config.kernels.metaswap.dll,
                lib_dependency=self.ribametamod_config.kernels.metaswap.dll_dep_dir,
                working_directory=self.ribametamod_config.kernels.metaswap.work_dir,
                timing=self.base_config.timing,
            )
            self.has_metaswap = True
        else:
            self.has_metaswap = False

        if self.has_metaswap and self.has_ribasim:
            self.msw.initialize_surface_water_component()

        # Print output to stdout
        self.mf6.set_int("ISTDOUTTOFILE", 0)
        self.mf6.initialize()
        ribasim_config_file = ""
        if self.has_ribasim and self.ribametamod_config.kernels.ribasim is not None:
            ribasim_config_file = str(
                self.ribametamod_config.kernels.ribasim.config_file
            )
            self.ribasim.init_julia()
            self.ribasim.initialize(ribasim_config_file)
        if self.has_metaswap:
            self.msw.initialize()
        self.log_version()

        if self.coupling.output_config_file is not None:
            self.exchange_logger = ExchangeCollector.from_file(
                self.coupling.output_config_file
            )
        else:
            self.exchange_logger = ExchangeCollector()
        self.couple()

    def check_msw_mf6_timesteps(self) -> None:
        delt_msw = self.msw.get_sw_time_step()
        delt_mf6 = self.mf6.get_time_step()
        if delt_msw != delt_mf6:
            raise ValueError(
                "Timestep length for fast proceses in MetaSWAP should be equal to the one for slow proceses"
            )

    def log_version(self) -> None:
        logger.info(f"MODFLOW version: {self.mf6.get_version()}")
        # Getting the version from ribasim does not work at the moment
        # https://github.com/Deltares/Ribasim/issues/364
        if self.has_metaswap:
            logger.info(f"MetaSWAP version: {self.msw.get_version()}")

    def couple(self) -> None:
        """Couple Modflow, MetaSWAP and Ribasim"""

        self.max_iter = self.mf6.max_iter()
        mf6_flowmodel_key = self.coupling.mf6_model
        self.mf6_head = self.mf6.get_head(mf6_flowmodel_key)

        # Get all MODFLOW 6 pointers, relevant for coupling with Ribasim
        if self.has_ribasim:
            self.mf6_active_river_packages = self.mf6.get_rivers_packages(
                mf6_flowmodel_key, list(self.coupling.mf6_active_river_packages.keys())
            )
            self.mf6_passive_river_packages = self.mf6.get_rivers_packages(
                mf6_flowmodel_key, list(self.coupling.mf6_passive_river_packages.keys())
            )
            self.mf6_active_drainage_packages = self.mf6.get_drainage_packages(
                mf6_flowmodel_key,
                list(self.coupling.mf6_active_drainage_packages.keys()),
            )
            self.mf6_passive_drainage_packages = self.mf6.get_drainage_packages(
                mf6_flowmodel_key,
                list(self.coupling.mf6_passive_drainage_packages.keys()),
            )
            self.mf6_river_packages = ChainMap(
                self.mf6_active_river_packages, self.mf6_passive_river_packages
            )
            self.mf6_drainage_packages = ChainMap(
                self.mf6_active_drainage_packages, self.mf6_passive_drainage_packages
            )

        # Get all MODFLOW 6 pointers, relevant for optional coupling with MetaSWAP
        if self.coupling.mf6_msw_recharge_pkg is not None:
            self.mf6_recharge = self.mf6.get_recharge(
                self.coupling.mf6_model, self.coupling.mf6_msw_recharge_pkg
            )
            self.mf6_recharge_nodes = self.mf6.get_recharge_nodes(
                self.coupling.mf6_model, self.coupling.mf6_msw_recharge_pkg
            )

        self.mf6_storage = self.mf6.get_storage(self.coupling.mf6_model)
        self.mf6_has_sc1 = self.mf6.has_sc1(self.coupling.mf6_model)
        self.mf6_area = self.mf6.get_area(self.coupling.mf6_model)
        self.mf6_top = self.mf6.get_top(self.coupling.mf6_model)
        self.mf6_bot = self.mf6.get_bot(self.coupling.mf6_model)

        # Get all relevant Ribasim pointers
        if self.has_ribasim:
            self.ribasim_infiltration = self.ribasim.get_value_ptr("infiltration")
            self.ribasim_drainage = self.ribasim.get_value_ptr("drainage")
            self.ribasim_level = self.ribasim.get_value_ptr("level")
            self.ribasim_volume = self.ribasim.get_value_ptr("volume")

        # Get all relevant MetaSWAP pointers
        if self.has_metaswap:
            self.msw_head = self.msw.get_head_ptr()
            self.msw_volume = self.msw.get_volume_ptr()
            self.msw_storage = self.msw.get_storage_ptr()

        # set mapping
        # Ribasim - MODFLOW 6
        ribmod_packages: ChainMap[str, Any] = ChainMap()
        if self.has_ribasim:
            ribmod_packages.update(
                ChainMap[str, Any](
                    self.mf6_river_packages,
                    self.mf6_drainage_packages,
                    {"ribasim_nbound": len(self.ribasim_level)},
                )
            )

        # MetaSWAP - MODFLOW 6
        mswmod_packages: dict[str, Any] = {}
        if self.has_metaswap:
            mswmod_packages["msw_head"] = self.msw_head
            mswmod_packages["msw_volume"] = self.msw_volume
            mswmod_packages["msw_storage"] = self.msw_storage
            mswmod_packages[
                "mf6_recharge"
            ] = self.mf6_recharge  # waar komt mf6_recharge vandaan
            if (
                self.coupling.enable_sprinkling_groundwater
                and self.coupling.mf6_msw_well_pkg is not None
            ):
                self.mf6_sprinkling_wells = self.mf6.get_well(
                    self.coupling.mf6_model, self.coupling.mf6_msw_well_pkg
                )
                mswmod_packages["mf6_sprinkling_wells"] = self.mf6_sprinkling_wells
            mswmod_packages["mf6_head"] = self.mf6_head
            mswmod_packages["mf6_storage"] = self.mf6_storage
            mswmod_packages["mf6_has_sc1"] = self.mf6_has_sc1
            mswmod_packages["mf6_area"] = self.mf6_area
            mswmod_packages["mf6_top"] = self.mf6_top
            mswmod_packages["mf6_bot"] = self.mf6_bot

        self.mapping = SetMapping(
            self.coupling,
            ChainMap(
                ribmod_packages,
                mswmod_packages,
            ),
            self.has_metaswap,
            self.has_ribasim,
            (
                self.msw.working_directory / "mod2svat.inp"
                if self.has_metaswap
                else None
            ),
        )

    def update(self) -> None:
        # TODO: Store a copy of the river bottom and the river elevation. The
        # river bottom and drainage elevation should not be fall below these
        # values. Note that the river bottom and the drainage elevation may be
        # update every stress period.

        # exchange stages from Ribasim to MODFLOW 6
        if self.has_ribasim:
            self.ribasim_infiltration[:] = 0.0
            self.ribasim_drainage[:] = 0.0
            self.exchange_rib2mod()

        # Do one MODFLOW 6 - MetaSWAP timestep
        if self.has_metaswap:
            self.exchange_mod2msw()
            self.mf6.prepare_time_step(0.0)
            self.delt = self.mf6.get_time_step()
            self.msw.prepare_time_step(self.delt)

            # Do one surface water timestep MetaSWAP
            self.msw.prepare_surface_water_time_step(1)  # dtgw == dtsw
            if self.has_ribasim:
                self.exchange_msw2rib()
            # for now we always realise the demand for sprinkling since we miss functionality in Ribasim
            # see: https://github.com/Deltares/Ribasim/issues/893
            # also the location of the exchange should be moved to after the Ribasim solve
            # see: https://github.com/Deltares/Ribasim/issues/894

            rib_sprfrac_realised = np.array(
                [0.0]
            )  # dummy fraction for now, shape = Ribasim users

            self.exchange_rib2msw(rib_sprfrac_realised)

            self.msw.finish_surface_water_time_step(1)

            self.solve_modflow6_metaswap()

            self.mf6.finalize_time_step()
            self.msw.finalize_time_step()
        else:
            self.mf6.update()

        if self.has_ribasim:
            # exchange drainage fluxes from MODFLOW 6 to Ribasim
            self.exchange_mod2rib()
            # Update Ribasim until current time of MODFLOW 6
            self.ribasim.update_until(
                self.get_current_time() * days_to_seconds(self.delt)
            )

    def solve_modflow6_metaswap(self) -> None:
        self.mf6.prepare_solve(1)
        for kiter in range(1, self.max_iter + 1):
            has_converged = self.do_modflow6_metaswap_iter(1)
            if has_converged:
                logger.debug(f"MF6-MSW converged in {kiter} iterations")
                break
        self.mf6.finalize_solve(1)

    def do_modflow6_metaswap_iter(self, sol_id: int) -> bool:
        """Execute a single iteration"""
        self.msw.prepare_solve(0)
        self.msw.solve(0)
        self.exchange_msw2mod()
        has_converged = self.mf6.solve(sol_id)
        self.exchange_mod2msw()
        self.msw.finalize_solve(0)
        return has_converged

    def exchange_msw2rib(self) -> None:
        if self.mapping.msw2rib is not None:
            # flux from metaswap ponding to Ribasim
            if "sw_ponding" in self.mapping.msw2rib:
                self.msw_ponding_flux_sec = (
                    self.msw.get_surfacewater_ponding_allocation_ptr()
                    / days_to_seconds(self.delt)
                )
                ribasim_flux_ponding = self.mapping.msw2rib["sw_ponding"].dot(
                    self.msw_ponding_flux_sec
                )[:]
                self.ribasim_drainage[:] += ribasim_flux_ponding[:]

            # flux from metaswap sprinkling to Ribasim (demand)
            if "sw_sprinkling" in self.mapping.msw2rib and self.coupling.enable_sprinkling_surface_water:
                self.msw_sprinkling_demand_sec = (
                    self.msw.get_surfacewater_sprinking_demand_ptr()
                    / days_to_seconds(self.delt)
                )

                ribasim_sprinkling_demand_sec = self.mapping.msw2rib["sw_sprinkling"].dot(
                    self.msw_sprinkling_demand_sec
                )[:]
                self.ribasim_infiltration += np.where(
                    ribasim_sprinkling_demand_sec > 0, ribasim_sprinkling_demand_sec, 0
                )
                self.ribasim_drainage += np.where(
                    ribasim_sprinkling_demand_sec < 0, -ribasim_sprinkling_demand_sec, 0
                )

    def exchange_rib2msw(self, rib_sprfrac_realised: NDArray[np.float64]) -> None:
        # realised flux from Ribasim to metaswap
        if self.coupling.enable_sprinkling_surface_water:
            msw_sprinkling_realised = self.msw.get_surfacewater_sprinking_realised_ptr()
            # map fractions back to the shape of MetaSWAP array
            msw_sprfrac_realised = self.mapping.msw2rib["sw_sprinkling"].T.dot(
                rib_sprfrac_realised
            )
            # multiply fractions with demands
            msw_sprinkling_realised[:] = (
                (self.msw_sprinkling_demand_sec * days_to_seconds(self.delt))
                * msw_sprfrac_realised
            )[:]

    def exchange_mod2rib(self) -> None:
        # Compute MODFLOW 6 river and drain flux
        for key, river in self.mf6_river_packages.items():
            river_flux = river.get_flux(self.mf6_head)
            ribasim_flux = self.mapping.mod2rib[key].dot(river_flux) / days_to_seconds(
                self.delt
            )
            self.ribasim_infiltration += np.where(ribasim_flux > 0, ribasim_flux, 0)
            self.ribasim_drainage += np.where(ribasim_flux < 0, -ribasim_flux, 0)

        for key, drainage in self.mf6_drainage_packages.items():
            drain_flux = drainage.get_flux(self.mf6_head)
            ribasim_flux = self.mapping.mod2rib[key].dot(drain_flux) / days_to_seconds(
                self.delt
            )
            self.ribasim_drainage -= ribasim_flux

    def exchange_rib2mod(self) -> None:
        # Set the MODFLOW 6 river stage and drainage to value of waterlevel of Ribasim basin
        for key, river in self.mf6_active_river_packages.items():
            # TODO: use specific level after Ribasim can export levels
            river.stage[:] = self.mapping.rib2mod[key].dot(self.ribasim_level)
        for key, drainage in self.mf6_active_drainage_packages.items():
            # TODO: use specific level after Ribasim can export levels
            drainage.elevation[:] = self.mapping.rib2mod[key].dot(self.ribasim_level)

    def exchange_msw2mod(self) -> None:
        """Exchange Metaswap to Modflow"""
        self.mf6_storage[:] = (
            self.mapping.msw2mod["storage_mask"][:] * self.mf6_storage[:]
            + self.mapping.msw2mod["storage"].dot(self.msw_storage)[:]
        )
        self.exchange_logger.log_exchange(
            "mf6_storage", self.mf6_storage, self.get_current_time()
        )
        self.exchange_logger.log_exchange(
            "msw_storage", self.msw_storage, self.get_current_time()
        )
        # Set recharge
        self.mf6_recharge[:] = (
            self.mapping.msw2mod["recharge_mask"][:] * self.mf6_recharge[:]
            + self.mapping.msw2mod["recharge"].dot(self.msw_volume)[:] / self.delt
        ) / self.mf6_area[self.mf6_recharge_nodes]

        if self.coupling.enable_sprinkling_groundwater:
            self.mf6_sprinkling_wells[:] = (
                self.mapping.msw2mod["sw_sprinkling_mask"][:]
                * self.mf6_sprinkling_wells[:]
                + self.mapping.msw2mod["sw_sprinkling"].dot(self.msw_volume)[:]
                / self.delt
            )

    def exchange_mod2msw(self) -> None:
        """Exchange Modflow to Metaswap"""
        self.msw_head[:] = (
            self.mapping.mod2msw["head_mask"][:] * self.msw_head[:]
            + self.mapping.mod2msw["head"].dot(self.mf6_head)[:]
        )

    def finalize(self) -> None:
        self.mf6.finalize()
        if self.has_ribasim:
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
        total_msw = self.msw.report_timing_totals()
        total = total_mf6 + total_ribasim + total_msw
        logger.info(f"Total elapsed time in numerical kernels: {total:0.4f} seconds")


def days_to_seconds(day: float) -> float:
    return day * 86400
