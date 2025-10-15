"""Ribamod: the coupling between MetaSWAP and MODFLOW 6

description:

"""

from __future__ import annotations

from collections import ChainMap
from typing import Any

import numpy as np
from loguru import logger
from numpy.typing import NDArray

from imod_coupler.config import BaseConfig
from imod_coupler.drivers.driver import Driver
from imod_coupler.drivers.ribametamod.config import Coupling, RibaMetaModConfig
from imod_coupler.drivers.ribametamod.exchange import CoupledExchangeBalance
from imod_coupler.drivers.ribametamod.mapping import (
    get_coupled_modflow_metaswap_nodes,
    get_coupled_ribasim_metaswap_nodes,
    get_coupled_ribasim_modflow_nodes,
)

# from imod_coupler.drivers.ribametamod.mapping import SetMapping
from imod_coupler.drivers.ribametamod.utils import (
    MemoryExchangeFractions,
    MemoryExchangeNegativeFractions,
    MemoryExchangePositiveFractions,
)
from imod_coupler.kernelwrappers.mf6_wrapper import (
    Mf6Api,
    Mf6Wrapper,
)
from imod_coupler.kernelwrappers.msw_wrapper import MswWrapper
from imod_coupler.kernelwrappers.ribasim_wrapper import RibasimWrapper
from imod_coupler.logging.exchange_collector import ExchangeCollector
from imod_coupler.utils import MemoryExchange


class RibaMetaMod(Driver):
    """The driver coupling Ribasim, MetaSWAP and MODFLOW 6"""

    base_config: BaseConfig  # the parsed information from the configuration file
    ribametamod_config: RibaMetaModConfig  # the parsed information from the configuration file specific to Ribametamod
    coupling_config: Coupling  # the coupling information
    timing: bool  # true, when timing is enabled
    mf6: Mf6Wrapper  # the MODFLOW 6 kernel
    ribasim: RibasimWrapper  # the Ribasim kernel
    has_ribasim: bool
    msw: MswWrapper  # the MetaSWAP kernel
    has_metaswap: bool  # configured with or without metaswap
    enable_sprinkling_groundwater: bool
    enable_sprinkling_surface_water: bool

    exchange_balance: (
        CoupledExchangeBalance  # deals with waterbalance between mf6 and Ribasim
    )
    couplings: dict[str, MemoryExchange] = {}  # deals with all exchanges

    # Ribasim variables
    ribasim_infiltration_save: NDArray[Any]
    ribasim_drainage_save: NDArray[Any]

    def __init__(self, base_config: BaseConfig, ribametamod_config: RibaMetaModConfig):
        """Constructs the `RibaMetaMod` object"""
        self.base_config = base_config
        self.ribametamod_config = ribametamod_config
        self.coupling_config = ribametamod_config.coupling[
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
            self.ribasim = RibasimWrapper(
                lib_path=self.ribametamod_config.kernels.ribasim.dll,
                lib_dependency=self.ribametamod_config.kernels.ribasim.dll_dep_dir,
                timing=self.base_config.timing,
            )
            self.ribasim.initialize_julia()  # only once per session
            self.has_ribasim = True
        else:
            self.has_ribasim = False

        if (
            self.ribametamod_config.kernels.metaswap is not None
            and self.coupling_config.mf6_msw_node_map is not None
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
            self.ribasim.initialize(ribasim_config_file)
            self.initialize_mf6_packages(self.coupling_config.mf6_model)
        if self.has_metaswap:
            self.msw.initialize()
            if self.has_ribasim:
                self.msw.initialize_surface_water_component()

        self.log_version()

        if self.coupling_config.output_config_file is not None:
            self.exchange_logger = ExchangeCollector.from_file(
                self.coupling_config.output_config_file
            )
        else:
            self.exchange_logger = ExchangeCollector()
        self.couple()

    def initialize_mf6_packages(self, mf6_flowmodel_key: str) -> None:
        active_river_packages = list(
            self.coupling_config.mf6_active_river_packages.keys()
        )
        active_drainage_packages = list(
            self.coupling_config.mf6_active_drainage_packages.keys()
        )
        self.mf6.set_rivers_packages(mf6_flowmodel_key, active_river_packages)
        self.mf6.set_drainage_packages(mf6_flowmodel_key, active_drainage_packages)
        self.active_packages = active_river_packages + active_drainage_packages
        passive_river_packages = list(
            self.coupling_config.mf6_passive_river_packages.keys()
        )
        passive_drainage_packages = list(
            self.coupling_config.mf6_passive_drainage_packages.keys()
        )
        self.mf6.set_rivers_packages(mf6_flowmodel_key, passive_river_packages)
        self.mf6.set_drainage_packages(mf6_flowmodel_key, passive_drainage_packages)
        self.passive_packages = passive_river_packages + passive_drainage_packages
        self.api_packages = ["api_" + key for key in active_river_packages]
        self.mf6.set_api_packages(mf6_flowmodel_key, self.api_packages)

    def log_version(self) -> None:
        logger.info(f"MODFLOW version: {self.mf6.get_version()}")
        if self.has_ribasim:
            logger.info(f"Ribasim version: {self.ribasim.get_version()}")
        if self.has_metaswap:
            logger.info(f"MetaSWAP version: {self.msw.get_version()}")

    def couple_ribasim(self) -> None:
        coupled_nodes = get_coupled_ribasim_modflow_nodes(
            ChainMap(
                self.coupling_config.mf6_active_river_packages,
                self.coupling_config.mf6_active_drainage_packages,
            )
        )
        for package_name, coupled_node in coupled_nodes.items():
            self.coupled_ribasim_basins[coupled_node["basin_index"]] = 1
            # stage rib -> mf6
            self.couplings[package_name + "_stage"] = MemoryExchange(
                ptr_a=self.ribasim.get_value_ptr("basin.subgrid_level"),
                ptr_b=self.mf6.packages[package_name].water_level,
                ptr_a_index=coupled_node["subgrid_index"],
                ptr_b_index=coupled_node["bound_index"],
                exchange_logger=self.exchange_logger,
                label="stage_" + package_name,
                exchange_operator="sum",
            )
            # q mf6 -> exchange balance
            self.couplings[package_name] = MemoryExchange(
                ptr_a=self.mf6.packages[package_name].q_estimate,
                ptr_b=self.exchange_balance.demands[package_name],
                ptr_a_index=coupled_node["bound_index"],
                ptr_b_index=coupled_node["basin_index"],
                ptr_b_conversion=np.full_like(
                    self.exchange_balance.demands[package_name], -1.0
                ),  # reverse sign convention mf6
                exchange_logger=self.exchange_logger,
                label="exchange_demand_" + package_name,
                exchange_operator="sum",

            )
            # q mf6 -> exchange balance for negative contributions only
            # use PositiveFraction since positive mf6 drainage == infiltration from Ribasim
            self.couplings[package_name + "_negative"] = (
                MemoryExchangePositiveFractions(
                    ptr_a=self.mf6.packages[package_name].q_estimate,
                    ptr_b=self.exchange_balance.demands_negative[package_name],
                    ptr_a_index=coupled_node["bound_index"],
                    ptr_b_index=coupled_node["basin_index"],
                    ptr_a_conversion=np.full_like(
                        self.mf6.packages[package_name].q_estimate, -1.0
                    ),
                    exchange_logger=self.exchange_logger,
                    label=package_name + "_exchange_demand_negative",
                    exchange_operator="sum",
                )
            )
            # q correction exchange balance -> mf6 api-package
            # only for river packages
            if package_name in self.coupling_config.mf6_active_river_packages:
                self.couplings["api_" + package_name] = MemoryExchangeNegativeFractions(
                    ptr_a_fractions=self.exchange_balance.realised_fraction,
                    ptr_b=self.mf6.packages["api_" + package_name].rhs,
                    ptr_bb=self.mf6.packages[package_name].q_estimate,
                    ptr_a_index=coupled_node["basin_index"],
                    ptr_b_index=coupled_node["bound_index"],
                    exchange_logger=self.exchange_logger,
                    label=package_name + "_exchange_demand_correction",
                    exchange_operator="sum",
                )
        coupled_passive_nodes = get_coupled_ribasim_modflow_nodes(
            ChainMap(
                self.coupling_config.mf6_passive_river_packages,
                self.coupling_config.mf6_passive_drainage_packages,
            )
        )
        for package_name, coupled_node in coupled_passive_nodes.items():
            # q mf6 -> exchange balance
            self.couplings[package_name] = MemoryExchange(
                ptr_a=self.mf6.packages[package_name].q_estimate,
                ptr_b=self.exchange_balance.demands[package_name],
                ptr_a_index=coupled_node["bound_index"],
                ptr_b_index=coupled_node["basin_index"],
                exchange_logger=self.exchange_logger,
                label=package_name + "_exchange_demand",
                exchange_operator="sum",
            )

    def couple_metaswap(self) -> None:
        # conversion terms:
        # by using 1.0 as numerator we assume a summmation for 1:n couplings
        # storage: MetaSWAP provides sc1*area, MODFLOW expects sc1 or ss
        mf6_area = self.mf6.get_area(self.coupling_config.mf6_model)
        if self.mf6.has_sc1(self.coupling_config.mf6_model):
            # mf6 expects sc1, MetaSWAP provides sc1*area
            conversion_terms_storage = 1.0 / mf6_area
        else:
            # mf6 expects ss, MetaSWAP provides sc1*area
            # sc1 = ss * layer thickness
            mf6_area = self.mf6.get_area(self.coupling_config.mf6_model)
            mf6_top = self.mf6.get_top(self.coupling_config.mf6_model)
            mf6_bot = self.mf6.get_bot(self.coupling_config.mf6_model)
            conversion_terms_storage = 1.0 / (mf6_area * (mf6_top - mf6_bot))
        # recharge: MetaSWAP provides volume, MODFLOW expects flux lentgh/time
        recharge_nodes = (
            self.mf6.get_recharge_nodes(
                self.coupling_config.mf6_model,
                self.coupling_config.mf6_msw_recharge_pkg,

            )
            - 1
        )
        conversion_terms_recharge_area = (
            1.0 / mf6_area[recharge_nodes]
        )  # volume to length

        assert self.coupling_config.mf6_msw_node_map is not None  # mypy
        assert self.coupling_config.mf6_msw_recharge_map is not None  # mypy
        assert self.ribametamod_config.kernels.metaswap is not None  # mypy

        coupled_nodes = get_coupled_modflow_metaswap_nodes(
            self.coupling_config.mf6_msw_node_map,
            self.coupling_config.mf6_msw_recharge_map,
            self.ribametamod_config.kernels.metaswap.work_dir,
            self.coupling_config.mf6_msw_sprinkling_map_groundwater,
        )
        self.couplings["storage"] = MemoryExchange(
            self.msw.get_storage_ptr(),
            self.mf6.get_storage(self.coupling_config.mf6_model),
            coupled_nodes["msw_gwf_nodes"],
            coupled_nodes["mf6_gwf_nodes"],
            self.exchange_logger,
            "storage",
            ptr_b_conversion=conversion_terms_storage,
        )
        self.couplings["recharge"] = MemoryExchange(
            self.msw.get_volume_ptr(),
            self.mf6.get_recharge(
                self.coupling_config.mf6_model,
                self.coupling_config.mf6_msw_recharge_pkg,
            ),
            coupled_nodes["msw_rch_nodes"],
            coupled_nodes["mf6_rch_nodes"],
            self.exchange_logger,
            "recharge",
            ptr_b_conversion=conversion_terms_recharge_area,
        )
        self.couplings["head"] = MemoryExchange(
            self.mf6.get_head(self.coupling_config.mf6_model),
            self.msw.get_head_ptr(),
            coupled_nodes["mf6_gwf_nodes"],
            coupled_nodes["msw_gwf_nodes"],
            self.exchange_logger,
            "head",
            exchange_operator="avg",
        )

        if self.enable_sprinkling_groundwater:
            assert isinstance(self.coupling_config.mf6_msw_well_pkg, str)
            self.couplings["sprinkling"] = MemoryExchange(
                self.msw.get_volume_ptr(),
                self.mf6.get_well(
                    self.coupling_config.mf6_model,
                    self.coupling_config.mf6_msw_well_pkg,
                ),
                coupled_nodes["msw_well_nodes"],
                coupled_nodes["mf6_well_nodes"],
                self.exchange_logger,
                "gw_sprinkling",
                exchange_operator="sum",
            )
            self.enable_sprinkling_groundwater = True
        # Get all MetaSWAP pointers, relevant for coupling with Ribasim
        if self.has_ribasim:
            coupled_nodes = get_coupled_ribasim_metaswap_nodes(
                self.coupling_config.rib_msw_ponding_map_surface_water,
                self.coupling_config.rib_msw_sprinkling_map_surface_water,
            )
            self.coupled_ribasim_basins[coupled_nodes["ribasim_ponding_nodes"]] = 1
            self.couplings["sw_ponding"] = MemoryExchange(
                self.msw.get_surfacewater_ponding_allocation_ptr(),
                self.exchange_balance.demands["sw_ponding"],
                coupled_nodes["metaswap_ponding_nodes"],
                coupled_nodes["ribasim_ponding_nodes"],
                self.exchange_logger,
                "exchange_demand_sw_ponding",
                exchange_operator="sum",
            )
            if "ribasim_sprinkling_nodes" in coupled_nodes.keys():
                self.ribasim.set_water_user_arrays()
                self.enable_sprinkling_surface_water = True
                self.couplings["sw_sprinkling_demand"] = MemoryExchange(
                    self.msw.get_surfacewater_sprinking_demand_ptr(),
                    self.ribasim.user_demand_flat,
                    coupled_nodes["metaswap_sprinkling_nodes"],
                    coupled_nodes["ribasim_sprinkling_nodes"],
                    self.exchange_logger,
                    "sw_sprinkling_demand",
                    ptr_a_conversion=np.full_like(
                        self.msw.get_surfacewater_sprinking_demand_ptr(),
                        -1.0,
                    ),  # reverse sign convention metaswap + m3/d -> m3/s
                    exchange_operator="sum",

                )
                self.couplings["sw_sprinkling_realised"] = MemoryExchangeFractions(
                    self.ribasim.user_realized_fraction,
                    self.msw.get_surfacewater_sprinking_realised_ptr(),
                    self.msw.get_surfacewater_sprinking_demand_ptr(),
                    coupled_nodes["ribasim_sprinkling_nodes"],
                    coupled_nodes["metaswap_sprinkling_nodes"],
                    self.exchange_logger,
                    "sw_sprinkling_realized",
                    exchange_operator="sum",
                )
                self.ribasim.set_coupled_user(
                    self.couplings["sw_sprinkling_demand"].mask
                )

    def couple(self) -> None:
        """Couple Modflow, MetaSWAP and Ribasim"""
        mf6_flowmodel_key = self.coupling_config.mf6_model
        self.mf6_head = self.mf6.get_head(mf6_flowmodel_key)

        if self.has_ribasim:
            self.coupled_ribasim_basins = np.zeros_like(
                self.ribasim.drainage_infiltration
            )
            self.exchange_balance = CoupledExchangeBalance(
                shape=self.ribasim.drainage_infiltration.size,
                labels=self.exchange_labels(),
                ribasim_kernel=self.ribasim,
                mf6_kernel=self.mf6,
                mf6_active_packages=self.active_packages,
                mf6_passive_packages=self.passive_packages,
                mf6_api_packages=self.api_packages,
            self.couple_ribasim()
            if self.has_metaswap:
                self.couple_metaswap()
        self.exchange_balance.couplings = self.couplings
        self.exchange_balance.coupled_basins = self.coupled_ribasim_basins == 1

    def update_ribasim_metaswap(self) -> None:
        nsubtimesteps = self.mf6.delt / self.msw.delt_sw
        self.msw.prepare_time_step_noSW(self.mf6.delt)

        for timestep_sw in range(1, int(nsubtimesteps) + 1):
            self.msw.prepare_surface_water_time_step(timestep_sw)
            self.exchange_balance.add_ponding_volume_msw()
            if self.enable_sprinkling_surface_water:
                self.exchange_sprinkling_demand_msw2rib()
            # exchange summed volumes to Ribasim
            self.exchange_balance.flux_to_ribasim(self.mf6.delt, self.msw.delt_sw)
            # update Ribasim per delt_sw
            self.current_time += self.msw.delt_sw
            self.ribasim.update_until(day_to_seconds * self.current_time)
            # get realised values on wateruser nodes
            if self.enable_sprinkling_surface_water:
                self.exchange_sprinkling_flux_realised_msw2rib()
            self.log_dtsw_log_exchanges_dtsw()
            self.msw.finish_surface_water_time_step(timestep_sw)

    def update_ribasim(self) -> None:
        # exchange summed volumes to Ribasim
        # no metaswap, delt_sw doesn't exist
        self.exchange_balance.flux_to_ribasim(self.mf6.delt, self.mf6.delt)
        # update Ribasim per delt_gw
        self.ribasim.update_until(day_to_seconds * self.get_current_time())

    def update(self) -> None:
        if self.has_metaswap:
            self.couplings["head"].exchange()

        self.mf6.prepare_time_step(0.0)

        if self.has_ribasim:
            self.exchange_rib2mod()
            self.exchange_mod2rib()

        if self.has_ribasim:
            if self.has_metaswap:
                self.update_ribasim_metaswap()
            else:
                self.update_ribasim()

            self.exchange_balance.flux_to_modflow(
                self.ribasim.compute_realized_drainage_infiltration(),
                self.mf6.delt,
            )

        # do the MODFLOW-MetaSWAP timestep
        if self.has_metaswap:
            self.solve_modflow6_metaswap()
        else:
            self.solve_modflow()
        self.mf6.finalize_time_step()
        if self.has_metaswap:
            self.msw.finalize_time_step()
        self.log_exchanges_dtgw()

    def solve_modflow(self) -> None:
        self.mf6.prepare_solve(1)
        for kiter in range(1, self.mf6.max_iter + 1):
            has_converged = self.do_modflow_iter(1)
            if has_converged:
                logger.debug(f"MF6 converged in {kiter} iterations")
                break
        self.mf6.finalize_solve(1)

    def solve_modflow6_metaswap(self) -> None:
        self.mf6.prepare_solve(1)
        for kiter in range(1, self.mf6.max_iter + 1):
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
        self.couplings["storage"].exchange()
        self.couplings["recharge"].exchange(self.mf6.delt)
        if self.enable_sprinkling_groundwater:
            self.couplings["sprinkling"].exchange(self.mf6.delt)
        has_converged = self.mf6.solve(sol_id)
        self.couplings["head"].exchange()
        self.msw.finalize_solve(0)
        return has_converged

    def finalize(self) -> None:
        self.mf6.finalize()
        if self.has_ribasim:
            self.ribasim.finalize()
        for coupling in self.couplings.values():
            coupling.finalize_log()

    def exchange_rib2mod(self) -> None:
        self.ribasim.update_subgrid_level()
        # zeros exchange-arrays, Ribasim pointers and API-packages
        self.exchange_balance.reset()
        # exchange stage and compute flux estimates over MODFLOW 6 timestep
        self.exchange_stage_rib2mod()

    def exchange_mod2rib(self) -> None:
        self.exchange_balance.add_flux_estimate_mod(self.mf6_head, self.mf6.delt)
        # reset Ribasim pointers
        self.ribasim.save_cumulative_drainage_infiltration()

    def exchange_sprinkling_demand_msw2rib(self) -> None:
        self.couplings["sw_sprinkling_demand"].exchange(
            delt=self.msw.delt_sw * day_to_seconds
        )  # m3/dtsw -> m3/s
        self.ribasim.exchange_demand_water_users()
        self.msw.get_surfacewater_sprinking_demand_ptr()

    def exchange_sprinkling_flux_realised_msw2rib(self) -> None:
        self.ribasim.set_realised_fraction_water_users(
            self.msw.delt_sw * day_to_seconds
        )
        self.couplings["sw_sprinkling_realised"].exchange()

    def exchange_stage_rib2mod(self) -> None:
        for package_name in self.active_packages:
            package = self.mf6.packages[package_name]
            if not isinstance(package, Mf6Api):  # mypy
                package.update_bottom_minimum()
                self.couplings[package_name + "_stage"].exchange()
                package.set_stage()

    def exchange_labels(self) -> list[str]:
        exchange_labels = []
        if self.has_metaswap:
            exchange_labels.append("sw_ponding")
        if self.has_ribasim:
            exchange_labels.extend(self.active_packages)
            exchange_labels.extend(self.passive_packages)
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

    def log_exchanges_dtgw(self) -> None:
        for key, coupling in self.couplings.items():
            if "sprinkling" not in key:
                coupling.log(self.current_time)

    def log_dtsw_log_exchanges_dtsw(self) -> None:
        for key, coupling in self.couplings.items():
            if "sprinkling" in key:
                coupling.log(self.current_time)
              
day_to_seconds = 86400.0
