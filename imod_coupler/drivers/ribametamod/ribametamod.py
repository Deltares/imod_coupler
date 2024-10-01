"""Ribamod: the coupling between MetaSWAP and MODFLOW 6

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

    enable_sprinkling_groundwater: bool
    enable_sprinkling_surface_water: bool

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
    ribasim_user_demand: NDArray[Any]
    ribasim_user_realized: NDArray[Any]

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
        self.enable_sprinkling_groundwater = False
        self.enable_sprinkling_surface_water = False

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

        if (
            self.ribametamod_config.kernels.metaswap is not None
            and self.coupling.mf6_msw_node_map is not None
        ):
            self.msw = MswWrapper(
                lib_path=self.ribametamod_config.kernels.metaswap.dll,
                lib_dependency=self.ribametamod_config.kernels.metaswap.dll_dep_dir,
                working_directory=self.ribametamod_config.kernels.metaswap.work_dir,
                timing=self.base_config.timing,
            )
            self.has_metaswap = True
        else:
            self.has_metaswap = False

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
            if self.has_ribasim:
                self.msw.initialize_surface_water_component()

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

    def couple_ribasim(self, mf6_flowmodel_key: str) -> ChainMap[str, Any]:
        arrays: ChainMap[str, Any] = ChainMap()
        if self.has_ribasim:
            # Get all MODFLOW 6 pointers, relevant for coupling with Ribasim
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
            self.mf6_active_packages = ChainMap(
                self.mf6_active_river_packages, self.mf6_active_drainage_packages
            )  # type: ignore
            # Get all Ribasim pointers, relevant for coupling with MODFLOW 6
            self.ribasim_infiltration = self.ribasim.get_value_ptr("basin.infiltration")
            self.ribasim_drainage = self.ribasim.get_value_ptr("basin.drainage")
            self.ribasim_infiltration_sum = self.ribasim.get_value_ptr(
                "basin.cumulative_infiltration"
            )
            self.ribasim_drainage_sum = self.ribasim.get_value_ptr(
                "basin.cumulative_drainage"
            )
            self.ribasim_level = self.ribasim.get_value_ptr("basin.level")
            self.ribasim_storage = self.ribasim.get_value_ptr("basin.storage")
            self.ribasim_user_demand = self.ribasim.get_value_ptr("user_demand.demand")
            self.ribasim_user_realized = self.ribasim.get_value_ptr(
                "user_demand.inflow"
            )
            self.subgrid_level = self.ribasim.get_value_ptr("basin.subgrid_level")

            # add to return ChainMap
            arrays.update(
                ChainMap[str, Any](
                    self.mf6_river_packages,
                    self.mf6_drainage_packages,
                    {
                        "ribasim_nbasin": len(self.ribasim_level),
                        "ribasim_nuser": len(self.ribasim_user_realized)
                        if self.ribasim_user_realized.ndim > 0
                        else 0,
                        "ribasim_nsubgrid": len(self.subgrid_level)
                        if self.subgrid_level.ndim > 0
                        else 0,
                    },
                )
            )
        return arrays

    def couple_metaswap(self) -> dict[str, Any]:
        arrays: dict[str, Any] = {}
        if self.has_metaswap:
            # Get all MODFLOW 6 pointers, relevant for coupling with MetaSWAP
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
            # Get all MetaSWAP pointers, relevant for coupling with MODLFOW 6
            self.msw_head = self.msw.get_head_ptr()
            self.msw_volume = self.msw.get_volume_ptr()
            self.msw_storage = self.msw.get_storage_ptr()
            # add to return dict
            arrays["msw_head"] = self.msw_head
            arrays["msw_volume"] = self.msw_volume
            arrays["msw_storage"] = self.msw_storage
            arrays["mf6_recharge"] = self.mf6_recharge
            arrays["mf6_head"] = self.mf6_head
            arrays["mf6_storage"] = self.mf6_storage
            arrays["mf6_has_sc1"] = self.mf6_has_sc1
            arrays["mf6_area"] = self.mf6_area
            arrays["mf6_top"] = self.mf6_top
            arrays["mf6_bot"] = self.mf6_bot

            if self.coupling.mf6_msw_sprinkling_map_groundwater is not None:
                self.enable_sprinkling_groundwater = True
                assert self.coupling.mf6_msw_well_pkg is not None  # mypy
                self.mf6_sprinkling_wells = self.mf6.get_well(
                    self.coupling.mf6_model, self.coupling.mf6_msw_well_pkg
                )
                arrays["mf6_sprinkling_wells"] = self.mf6_sprinkling_wells

            # Get all MetaSWAP pointers, relevant for coupling with Ribasim
            if self.has_ribasim:
                self.msw_ponding_volume = (
                    self.msw.get_surfacewater_ponding_allocation_ptr()
                )
                self.delt_sw = self.msw.get_sw_time_step()
                # add to return dict
                arrays["ribmsw_nbound"] = np.size(
                    self.msw.get_surfacewater_ponding_allocation_ptr()
                )
        return arrays

    def couple(self) -> None:
        """Couple Modflow, MetaSWAP and Ribasim"""
        self.max_iter = self.mf6.max_iter()
        mf6_flowmodel_key = self.coupling.mf6_model
        self.mf6_head = self.mf6.get_head(mf6_flowmodel_key)

        # get all relevant pointers
        modrib_arrays = self.couple_ribasim(mf6_flowmodel_key)
        modribmsw_arrays = self.couple_metaswap()

        # set mappings
        self.mapping = SetMapping(
            self.coupling,
            ChainMap(
                modrib_arrays,
                modribmsw_arrays,
            ),
            self.has_metaswap,
            self.has_ribasim,
            (
                self.msw.working_directory / "mod2svat.inp"
                if self.has_metaswap
                else None
            ),
        )

        if self.has_ribasim:
            if self.has_metaswap:
                if self.coupling.rib_msw_sprinkling_map_surface_water is not None:
                    self.enable_sprinkling_surface_water = True
                    if self.ribasim_user_realized is not None:
                        self.realised_fractions_swspr: NDArray[np.float64] = (
                            np.full_like(self.ribasim_user_realized, 0.0)
                        )
                    modribmsw_arrays["rib_sprinkling_realized"] = (
                        self.ribasim_user_realized
                    )
                    modribmsw_arrays["rib_sprinkling_demand"] = self.ribasim_user_demand
                    n_users = self.ribasim_user_realized.size
                    n_priorities = self.ribasim_user_demand.size // n_users
                    self.ribasim_user_demand.resize(n_priorities, n_users)
                    self.coupled_user_indices = np.flatnonzero(
                        self.mapping.msw2rib["sw_sprinkling_mask"] == 0
                    )
                    self.coupled_priority_indices, _ = np.nonzero(
                        self.ribasim_user_demand[:, self.coupled_user_indices]
                    )

                    # check for multiple priorities per user
                    unique, counts = np.unique(
                        self.coupled_user_indices, return_counts=True
                    )
                    too_many = unique[counts > 1] + 1
                    if np.size(too_many) > 0:
                        raise ValueError(
                            f"More than one priority set for sprinkling user demands {too_many}."
                        )

                    # zero all coupled demand elements
                    self.ribasim_user_demand[
                        self.coupled_priority_indices, self.coupled_user_indices
                    ] = 0.0
            # Set exchange-class to handle all exchanges to Ribasim Basins
            self.exchange = CoupledExchangeBalance(
                shape=self.ribasim_infiltration.size,
                labels=self.exchange_labels(),
                mf6_river_packages=self.mf6_river_packages,
                mf6_drainage_packages=self.mf6_drainage_packages,
                mf6_active_river_api_packages=self.mf6_active_river_api_packages,
                mapping=self.mapping,
                ribasim_infiltration=self.ribasim_infiltration,
                ribasim_drainage=self.ribasim_drainage,
                exchange_logger=self.exchange_logger,
            )

    def update_ribasim_metaswap(self) -> None:
        nsubtimesteps = self.delt_gw / self.delt_sw
        self.msw.prepare_time_step_noSW(self.delt_gw)

        for timestep_sw in range(1, int(nsubtimesteps) + 1):
            self.msw.prepare_surface_water_time_step(timestep_sw)
            self.exchange.add_ponding_volume_msw(self.msw_ponding_volume)
            if self.enable_sprinkling_surface_water:
                self.exchange_sprinkling_demand_msw2rib()
                self.ribasim_user_realized[:] = (
                    0.0  # reset cummulative for the next timestep
                )
            # exchange summed volumes to Ribasim
            self.exchange.flux_to_ribasim(self.delt_gw, self.delt_sw)
            # update Ribasim per delt_sw
            self.current_time += self.delt_sw
            self.ribasim.update_until(day_to_seconds * self.current_time)
            # get realised values on wateruser nodes
            if self.enable_sprinkling_surface_water:
                self.exchange_sprinkling_flux_realised_msw2rib()
            self.msw.finish_surface_water_time_step(timestep_sw)

    def update_ribasim(self) -> None:
        # exchange summed volumes to Ribasim
        self.exchange.flux_to_ribasim(self.delt_gw, self.delt_gw)
        # update Ribasim per delt_gw
        self.ribasim.update_until(day_to_seconds * self.get_current_time())

    def update(self) -> None:
        if self.has_metaswap:
            self.exchange_mod2msw()

        self.mf6.prepare_time_step(0.0)
        self.delt_gw = self.mf6.get_time_step()

        if self.has_ribasim:
            self.exchange_rib2mod()
            self.exchange_mod2rib()

        if self.has_ribasim:
            if self.has_metaswap:
                self.update_ribasim_metaswap()
            else:
                self.update_ribasim()
            self.exchange.flux_to_modflow(
                (self.ribasim_drainage_sum - self.ribasim_infiltration_sum),
                self.delt_gw,
            )
            self.exchange.log_demands(self.get_current_time())

        # do the MODFLOW-MetaSWAP timestep
        if self.has_metaswap:
            self.solve_modflow6_metaswap()
        else:
            self.solve_modflow()
        self.mf6.finalize_time_step()
        if self.has_metaswap:
            self.msw.finalize_time_step()

    def solve_modflow(self) -> None:
        self.mf6.prepare_solve(1)
        for kiter in range(1, self.max_iter + 1):
            has_converged = self.do_modflow_iter(1)
            if has_converged:
                logger.debug(f"MF6 converged in {kiter} iterations")
                break
        self.mf6.finalize_solve(1)

    def solve_modflow6_metaswap(self) -> None:
        self.mf6.prepare_solve(1)
        for kiter in range(1, self.max_iter + 1):
            has_converged = self.do_modflow6_metaswap_iter(1)
            if has_converged:
                logger.debug(f"MF6-MSW converged in {kiter} iterations")
                break
        self.mf6.finalize_solve(1)

    def do_modflow_iter(self, sol_id: int) -> bool:
        """Execute a single iteration"""
        has_converged = self.mf6.solve(sol_id)
        return has_converged

    def do_modflow6_metaswap_iter(self, sol_id: int) -> bool:
        """Execute a single iteration"""
        self.msw.prepare_solve(0)
        self.msw.solve(0)
        self.exchange_msw2mod()
        has_converged = self.mf6.solve(sol_id)
        self.exchange_mod2msw()
        self.msw.finalize_solve(0)
        return has_converged

    def finalize(self) -> None:
        self.mf6.finalize()
        if self.has_ribasim:
            self.ribasim.finalize()
            self.ribasim.shutdown_julia()
        self.exchange_logger.finalize()

    def exchange_rib2mod(self) -> None:
        self.ribasim.update_subgrid_level()
        # zeros exchange-arrays, Ribasim pointers and API-packages
        self.exchange.reset()
        # exchange stage and compute flux estimates over MODFLOW 6 timestep
        self.exchange_stage_rib2mod()

    def exchange_mod2rib(self) -> None:
        self.exchange.add_flux_estimate_mod(self.mf6_head, self.delt_gw)
        # reset Ribasim pointers
        self.ribasim_infiltration_sum[:] = 0.0
        self.ribasim_drainage_sum[:] = 0.0

    def exchange_sprinkling_demand_msw2rib(self) -> None:
        # flux demand from metaswap sprinkling to Ribasim (demand)
        self.msw_sprinkling_demand_sec = (
            self.msw.get_surfacewater_sprinking_demand_ptr()
            / (self.delt_sw * day_to_seconds)
        )

        self.mapped_sprinkling_demand = self.mapping.msw2rib["sw_sprinkling"].dot(
            -self.msw_sprinkling_demand_sec
        )  # flip sign since ribasim expect a positive value for demand
        self.ribasim_user_demand[
            self.coupled_priority_indices, self.coupled_user_indices
        ] = self.mapped_sprinkling_demand[self.coupled_user_indices]

        self.exchange_logger.log_exchange(
            ("sprinkling_demand"),
            self.msw.get_surfacewater_sprinking_demand_ptr(),
            self.current_time,
        )

    def exchange_sprinkling_flux_realised_msw2rib(self) -> None:
        msw_sprinkling_realized = self.msw.get_surfacewater_sprinking_realised_ptr()

        nonzero_user_indices = np.flatnonzero(self.mapped_sprinkling_demand)

        self.realised_fractions_swspr[:] = 1.0  # all realized for non-coupled svats
        self.realised_fractions_swspr[nonzero_user_indices] = (
            self.ribasim_user_realized[nonzero_user_indices]
            / (self.delt_sw * day_to_seconds)
        ) / self.mapped_sprinkling_demand[nonzero_user_indices]

        msw_sprfrac_realised = (
            self.realised_fractions_swspr * self.mapping.msw2rib["sw_sprinkling"]
        )
        msw_sprinkling_realized[:] = (
            self.msw.get_surfacewater_sprinking_demand_ptr() * msw_sprfrac_realised
        )[:]
        self.ribasim_user_realized[:] = 0.0  # reset cummulative for the next timestep
        self.exchange_logger.log_exchange(
            ("sprinkling_realized"),
            msw_sprinkling_realized,
            self.current_time,
        )

    def exchange_stage_rib2mod(self) -> None:
        # Mypy refuses to understand this ChainMap for some reason.
        # ChainMaps work fine in other places...
        for key, package in self.mf6_active_packages.items():
            package.update_bottom_minimum()
            package.set_water_level(
                self.mapping.mask_rib2mod[key] * package.water_level
                + self.mapping.map_rib2mod_stage[key].dot(self.subgrid_level)
            )
            self.exchange_logger.log_exchange(
                ("stage_" + key), package.water_level, self.get_current_time()
            )

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

        if self.enable_sprinkling_groundwater:
            self.mf6_sprinkling_wells[:] = (
                self.mapping.msw2mod["gw_sprinkling_mask"][:]
                * self.mf6_sprinkling_wells[:]
                + self.mapping.msw2mod["gw_sprinkling"].dot(self.msw_volume)[:]
                / self.delt_gw
            )

    def exchange_mod2msw(self) -> None:
        """Exchange Modflow to Metaswap"""
        self.msw_head[:] = (
            self.mapping.mod2msw["head_mask"][:] * self.msw_head[:]
            + self.mapping.mod2msw["head"].dot(self.mf6_head)[:]
        )

    def exchange_labels(self) -> list[str]:
        exchange_labels = []
        if self.has_metaswap:
            exchange_labels.append("sw_ponding")
        if self.has_ribasim:
            exchange_labels.extend(list(self.mf6_active_river_packages.keys()))
            exchange_labels.extend(list(self.mf6_passive_river_packages.keys()))
            exchange_labels.extend(list(self.mf6_active_drainage_packages.keys()))
            exchange_labels.extend(list(self.mf6_passive_drainage_packages.keys()))
        return exchange_labels

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


day_to_seconds = 86400.0
