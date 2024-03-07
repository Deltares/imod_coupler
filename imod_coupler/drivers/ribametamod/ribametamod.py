""" Ribamod: the coupling between MetaSWAP and MODFLOW 6

description:

"""
from __future__ import annotations

from collections import ChainMap
from collections.abc import Sequence
from typing import Any

import numpy as np
from loguru import logger
from numpy.typing import NDArray
from ribasim_api import RibasimApi

from imod_coupler.config import BaseConfig
from imod_coupler.drivers.driver import Driver
from imod_coupler.drivers.ribametamod.config import Coupling, RibaMetaModConfig
from imod_coupler.drivers.ribametamod.exchange import CoupledExchangeBalance
from imod_coupler.drivers.ribametamod.mapping import SetMapping
from imod_coupler.kernelwrappers.mf6_wrapper import (
    Mf6Api,
    Mf6Drainage,
    Mf6River,
    Mf6Wrapper,
)
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
    exchange: CoupledExchangeBalance  # deals with exchanges to Ribasim

    max_iter: NDArray[Any]  # max. nr outer iterations in MODFLOW kernel
    delt_gw: float  # time step from MODFLOW 6 (leading)
    delt_sw: float  # surface water time step from MetaSWAP (leading)

    mf6_head: NDArray[Any]  # the hydraulic head array in the coupled model
    mf6_recharge: NDArray[Any]  # the coupled recharge array from the RCH package
    mf6_recharge_nodes: NDArray[Any]  # node selection of rch nodes
    mf6_storage: NDArray[Any]  # the specific storage array (ss)
    mf6_has_sc1: bool  # when true, specific storage in mf6 is given as a storage coefficient (sc1)
    mf6_area: NDArray[Any]  # cell area (size:nodes)
    mf6_top: NDArray[Any]  # top of cell (size:nodes)
    mf6_bot: NDArray[Any]  # bottom of cell (size:nodes)

    mf6_active_river_packages: dict[str, Mf6River]
    mf6_active_river_api_packages: dict[str, Mf6Api]
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
        self.current_time = self.get_current_time()
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

    def log_version(self) -> None:
        logger.info(f"MODFLOW version: {self.mf6.get_version()}")
        if self.has_ribasim:
            logger.info(f"Ribasim version: {self.ribasim.get_version()}")
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
            self.mf6_active_river_api_packages = self.get_api_packages(
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
            self.ribasim_infiltration = self.ribasim.get_value_ptr("basin.infiltration")
            self.ribasim_drainage = self.ribasim.get_value_ptr("basin.drainage")
            self.ribasim_level = self.ribasim.get_value_ptr("basin.level")
            self.ribasim_volume = self.ribasim.get_value_ptr("basin.storage")

        # Get all relevant MetaSWAP pointers
        if self.has_metaswap:
            self.msw_head = self.msw.get_head_ptr()
            self.msw_volume = self.msw.get_volume_ptr()
            self.msw_storage = self.msw.get_storage_ptr()
            self.msw_ponding = self.msw.get_surfacewater_ponding_allocation_ptr()
            self.delt_sw = self.msw.get_sw_time_step()

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

        # MetaSWAP - Ribasim
        if self.has_ribasim and self.has_metaswap:
            ribmsw_packages: dict[str, Any] = {}
            ribmsw_packages["mf6_bot"] = self.mf6_bot
            ribmsw_packages["ribmsw_nbound"] = np.size(
                self.msw.get_surfacewater_ponding_allocation_ptr()
            )

        self.mapping = SetMapping(
            self.coupling,
            ChainMap(
                ribmod_packages,
                mswmod_packages,
                ribmsw_packages,
            ),
            self.has_metaswap,
            self.has_ribasim,
            (
                self.msw.working_directory / "mod2svat.inp"
                if self.has_metaswap
                else None
            ),
        )

        # Set CoupledExchangeClass to handle all exchanges to Ribasim Basins
        labels = []
        if self.has_metaswap:
            labels.append("sw_ponding")
        if self.has_ribasim:
            labels.extend(list(self.mf6_active_river_packages.keys()))
            labels.extend(list(self.mf6_passive_river_packages.keys()))
            labels.extend(list(self.mf6_active_drainage_packages.keys()))
            labels.extend(list(self.mf6_passive_drainage_packages.keys()))
            self.exchange = CoupledExchangeBalance(
                shape=self.ribasim_infiltration.size,
                labels=labels,
                mf6_river_packages=self.mf6_river_packages,
                mf6_drainage_packages=self.mf6_drainage_packages,
                mf6_active_river_api_packages=self.mf6_active_river_api_packages,
                mapping=self.mapping,
                ribasim_infiltration=self.ribasim_infiltration,
                ribasim_drainage=self.ribasim_drainage,
            )

    def update(self) -> None:
        if self.has_metaswap:
            self.exchange_head_mod2msw()

        self.mf6.prepare_time_step(0.0)
        self.delt_gw = self.mf6.get_time_step()
        self.subtimesteps_sw = range(1, int(self.delt_gw / self.delt_sw) + 1)

        if self.has_ribasim:
            # zeros exchange-arrays, Ribasim pointers and API-packages
            self.exchange.reset()
            # exchange stage and compute flux estimates over MODFLOW 6 timestep
            self.exchange_stage_rib2mod()
            self.exchange.add_flux_estimate_mod(self.delt_gw, self.mf6_head)

        if self.has_metaswap and self.has_ribasim:
            self.msw.prepare_time_step(self.delt_sw)
            for timestep_sw in self.subtimesteps_sw:
                self.msw.prepare_surface_water_time_step(timestep_sw)
                self.exchange.add_ponding_msw(self.delt_sw, self.msw_ponding)
                self.exchange_sprinkling_demand_msw2rib(self.delt_sw)
                # exchange summed volumes to Ribasim
                self.exchange.to_ribasim()
                # update Ribasim per delt_sw
                self.current_time += self.current_time + self.delt_sw
                self.ribasim.update_until(
                    self.current_time * days_to_seconds(self.delt_sw)
                )
                # get realised values on wateruser nodes
                fraction_realised_user_nodes = np.array([0.0])  # dummy values for now
                # exchange realised sprinkling
                self.exchange_sprinkling_flux_realised_msw2rib(
                    fraction_realised_user_nodes
                )
                self.msw.finish_surface_water_time_step(timestep_sw)
        elif self.has_ribasim:
            # exchange summed volumes to Ribasim
            self.exchange.to_ribasim()
            # update Ribasim per delt_sw
            self.current_time += self.current_time + self.delt_gw
            self.ribasim.update_until(self.current_time * days_to_seconds(self.delt_gw))

        if self.has_ribasim:
            # get realised values on basin boundary nodes and exchange correction flux
            realised_basin_nodes = self.exchange.demand  # dummy value for now
            self.exchange.to_modflow(realised_basin_nodes)

        # do the MODFLOW-MetaSWAP timestep
        if self.has_metaswap:
            self.solve_modflow6_metaswap()
        else:
            self.mf6.update()
        self.mf6.finalize_time_step()
        if self.has_metaswap:
            self.msw.finalize_time_step()

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
        self.exchange_head_mod2msw()
        self.msw.finalize_solve(0)
        return has_converged

    def exchange_sprinkling_demand_msw2rib(self, delt: float) -> None:
        # flux demand from metaswap sprinkling to Ribasim (demand)
        if (
            "sw_sprinkling" in self.mapping.msw2rib
            and self.coupling.enable_sprinkling_surface_water
        ):
            self.msw_sprinkling_demand_sec = (
                self.msw.get_surfacewater_sprinking_demand_ptr() / days_to_seconds(delt)
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

    def exchange_sprinkling_flux_realised_msw2rib(
        self, realised_fractions: NDArray[np.float64]
    ) -> None:
        # realised flux from Ribasim to metaswap
        if self.coupling.enable_sprinkling_surface_water:
            msw_sprinkling_realised = self.msw.get_surfacewater_sprinking_realised_ptr()
            # map fractions back to the shape of MetaSWAP array
            msw_sprfrac_realised = self.mapping.msw2rib["sw_sprinkling"].T.dot(
                realised_fractions
            )
            # multiply fractions with demands
            msw_sprinkling_realised[:] = (
                (self.msw_sprinkling_demand_sec * days_to_seconds(self.delt_gw))
                * msw_sprfrac_realised
            )[:]

    def exchange_stage_rib2mod(self) -> None:
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
            + self.mapping.msw2mod["recharge"].dot(self.msw_volume)[:] / self.delt_gw
        ) / self.mf6_area[self.mf6_recharge_nodes - 1]

        if self.coupling.enable_sprinkling_groundwater:
            self.mf6_sprinkling_wells[:] = (
                self.mapping.msw2mod["sw_sprinkling_mask"][:]
                * self.mf6_sprinkling_wells[:]
                + self.mapping.msw2mod["sw_sprinkling"].dot(self.msw_volume)[:]
                / self.delt_gw
            )

    def exchange_head_mod2msw(self) -> None:
        """Exchange Modflow to Metaswap"""
        if self.has_metaswap:
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

    def get_api_packages(
        self, mf6_flowmodel_key: str, mf6_active_river_packages: Sequence[str]
    ) -> dict[str, Mf6Api]:
        api_packages = self.mf6.get_api_packages(
            mf6_flowmodel_key, ["api_" + key for key in mf6_active_river_packages]
        )
        return_labels = [key.replace("api_", "") for key in api_packages.keys()]
        return_values = api_packages.values()
        return dict(zip(return_labels, return_values))


def days_to_seconds(day: float) -> float:
    return day * 86400
