"""MetaMod: the coupling between MetaSWAP and MODFLOW 6

description:

"""

from __future__ import annotations

from typing import Any

import numpy as np
from loguru import logger
from numpy.typing import NDArray

from imod_coupler.config import BaseConfig
from imod_coupler.drivers.driver import Driver
from imod_coupler.drivers.metamod.config import MetaModConfig
from imod_coupler.utils import MemoryExchange
from imod_coupler.kernelwrappers.mf6_wrapper import Mf6Wrapper
from imod_coupler.kernelwrappers.msw_wrapper import MswWrapper
from imod_coupler.logging.exchange_collector import ExchangeCollector

from pathlib import Path

class MetaMod(Driver):
    """The driver coupling MetaSWAP and MODFLOW 6"""

    base_config: BaseConfig  # the parsed information from the configuration file
    metamod_config: MetaModConfig  # the parsed information from the configuration file specific to MetaMod

    timing: bool  # true, when timing is enabled
    mf6: Mf6Wrapper  # the MODFLOW 6 XMI kernel
    msw: MswWrapper  # the MetaSWAP XMI kernel

    max_iter: NDArray[Any]  # max. nr outer iterations in MODFLOW kernel
    delt: float  # time step from MODFLOW 6 (leading)

    def __init__(self, base_config: BaseConfig, metamod_config: MetaModConfig):
        """Constructs the `MetaMod` object"""
        self.base_config = base_config
        self.metamod_config = metamod_config
        self.coupling_configs = metamod_config.coupling

    def initialize(self) -> None:
        self.mf6 = Mf6Wrapper(
            lib_path=self.metamod_config.kernels.modflow6.dll,
            lib_dependency=self.metamod_config.kernels.modflow6.dll_dep_dir,
            working_directory=self.metamod_config.kernels.modflow6.work_dir,
            timing=self.base_config.timing,
        )
        self.msw = MswWrapper(
            lib_path=self.metamod_config.kernels.metaswap.dll,
            lib_dependency=self.metamod_config.kernels.metaswap.dll_dep_dir,
            working_directory=self.metamod_config.kernels.metaswap.work_dir,
            timing=self.base_config.timing,
        )
        # Print output to stdout
        self.mf6.set_int("ISTDOUTTOFILE", 0)
        self.mf6.initialize()
        self.msw.initialize()
        self.initialize_couplings()
        self.log_version()

    def initialize_exchange_logger_per_gwf_model(self, output_config_file: Path | None) -> ExchangeCollector:
        if output_config_file is not None:
            exchange_logger = ExchangeCollector.from_file(
                output_config_file
            )
        else:
            exchange_logger = ExchangeCollector()
        return exchange_logger

    def get_coupling_tables_per_gwf_model(
            self, 
            mf6_msw_node_map: Path, 
            mf6_msw_recharge_map: Path, 
            mf6_msw_sprinkling_map_groundwater: Path | None
            ) -> dict[str,tuple[NDArray[np.int32], NDArray[np.int32]]]:
        # create a lookup, with the svat tuples (id, lay) as keys and the
        # metaswap internal indexes as values
        svat_lookup = {}
        msw_mod2svat_file = self.msw.working_directory / "mod2svat.inp"
        if msw_mod2svat_file.is_file():
            svat_data: NDArray[np.int32] = np.loadtxt(
                msw_mod2svat_file, dtype=np.int32, ndmin=2
            )
            svat_id = svat_data[:, 1]
            svat_lay = svat_data[:, 2]
            for vi in range(svat_id.size):
                svat_lookup[(svat_id[vi], svat_lay[vi])] = vi
        else:
            raise ValueError(f"Can't find {msw_mod2svat_file}.")
        coupling_tables = {}
        gwf_table = np.loadtxt(mf6_msw_node_map,
             dtype=np.int32, ndmin=2
        )
        coupling_tables['mf6_gwf_nodes'] = gwf_table[:, 0] - 1  # mf6 nodes are one based
        coupling_tables['msw_gwf_nodes'] = np.array(
            [
                svat_lookup[gwf_table[ii, 1], gwf_table[ii, 2]]
                for ii in range(len(gwf_table))
            ],
            dtype=np.int32,
        )
        rch_table: NDArray[np.int32] = np.loadtxt(
            mf6_msw_recharge_map, dtype=np.int32, ndmin=2
        )
        coupling_tables['mf6_rch_nodes'] = rch_table[:, 0] - 1
        coupling_tables['msw_rch_nodes'] = [
            svat_lookup[rch_table[ii, 1], rch_table[ii, 2]]
            for ii in range(len(rch_table))
        ]
        if mf6_msw_sprinkling_map_groundwater is not None:
            well_table: NDArray[np.int32] = np.loadtxt(
                mf6_msw_sprinkling_map_groundwater,
                dtype=np.int32,
                ndmin=2,
            )
            coupling_tables['mf6_well_nodes'] = well_table[:, 0] - 1
            coupling_tables['msw_well_nodes'] = [
                svat_lookup[well_table[ii, 1], well_table[ii, 2]]
                for ii in range(len(well_table))
            ]
            self.enable_sprinkling_groundwater = True
        return coupling_tables

    def initialize_couplings_per_gwf_model(
            self, 
            coupled_nodes: dict[str,tuple[NDArray[np.int32], NDArray[np.int32]]], 
            exchange_logger: dict[str,ExchangeCollector], 
            mf6_model: str, 
            mf6_msw_recharge_pkg: str, 
            mf6_msw_well_pkg: str | None
        ) -> None:
        # conversion terms:
        # by using 1.0 as numerator we assume a summmation for 1:n couplings
        # storage: MetaSWAP provides sc1*area, MODFLOW expects sc1 or ss
        mf6_area = self.mf6.get_area(mf6_model)
        if self.mf6.has_sc1(mf6_model):
            # mf6 expects sc1, MetaSWAP provides sc1*area
            conversion_terms_storage = 1.0 / mf6_area
        else:
            # mf6 expects ss, MetaSWAP provides sc1*area
            # sc1 = ss * layer thickness
            mf6_top = self.mf6.get_top(mf6_model)
            mf6_bot = self.mf6.get_bot(mf6_model)
            conversion_terms_storage = 1.0 / (mf6_area * (mf6_top - mf6_bot))
        # recharge: MetaSWAP provides volume, MODFLOW expects flux lentgh/time
        recharge_nodes = (
            self.mf6.get_recharge_nodes(
                mf6_model,
                mf6_msw_recharge_pkg,
            )
            - 1
        )
        conversion_terms_recharge_area = (
            1.0 / mf6_area[recharge_nodes]
        )  # volume to length

        # set couplings
        couplings = {}
        couplings: dict[str, MemoryExchange] = {
            "storage": MemoryExchange(
                self.msw.get_storage_ptr(),
                self.mf6.get_storage(mf6_model),
                coupled_nodes['msw_gwf_nodes'],
                coupled_nodes['mf6_gwf_nodes'],
                exchange_logger,
                "storage",
                ptr_b_conversion=conversion_terms_storage,
            ),
            "recharge": MemoryExchange(
                self.msw.get_volume_ptr(),
                self.mf6.get_recharge(
                    mf6_model,
                    mf6_msw_recharge_pkg,
                ),
                coupled_nodes['msw_rch_nodes'],
                coupled_nodes['mf6_rch_nodes'],
                exchange_logger,
                "recharge",
                ptr_b_conversion=conversion_terms_recharge_area,
            ),
            "head": MemoryExchange(
                self.mf6.get_head(mf6_model),
                self.msw.get_head_ptr(),
                coupled_nodes['mf6_gwf_nodes'],
                coupled_nodes['msw_gwf_nodes'],
                exchange_logger,
                "head",
                exchange_operator="avg",
            ),
        }
        couplings["sprinkling"] = None
        if mf6_msw_well_pkg is not None:
            assert isinstance(mf6_msw_well_pkg, str)
            couplings["sprinkling"] = MemoryExchange(
                self.msw.get_volume_ptr(),
                self.mf6.get_well(
                    mf6_model,
                    mf6_msw_well_pkg,
                ),
                coupled_nodes['msw_well_nodes'],
                coupled_nodes['mf6_well_nodes'],
                exchange_logger,
                "sprinkling",
                exchange_operator="sum"
            )
        return couplings


    def initialize_couplings(self) -> None:
        self.couplings: dict[str, list] = {
        "storage": [],
        "recharge": [],
        "head": [],
        "sprinkling": [],
        }
        # initialize couplings for all gwf-models
        for coupling_config in self.coupling_configs:
            gwf_model = coupling_config.mf6_model
            coupled_nodes = self.get_coupling_tables_per_gwf_model(
                coupling_config.mf6_msw_node_map,
                coupling_config.mf6_msw_recharge_map,
                coupling_config.mf6_msw_sprinkling_map_groundwater
            )
            exchange_logger = self.initialize_exchange_logger_per_gwf_model(coupling_config.output_config_file)
            couplings = self.initialize_couplings_per_gwf_model(
                coupled_nodes,
                exchange_logger,
                gwf_model,
                coupling_config.mf6_msw_recharge_pkg, 
                coupling_config.mf6_msw_well_pkg
            )
            # append as to list of gwf-model exchanges per exchange type
            [self.couplings[coupling].append(couplings[coupling]) for coupling in  self.couplings.keys()]

    def log_version(self) -> None:
        logger.info(f"MODFLOW version: {self.mf6.get_version()}")
        logger.info(f"MetaSWAP version: {self.msw.get_version()}")

    def update(self) -> None:
        # heads to MetaSWAP for all coupled gwf-models
        [head.exchange() for head in self.couplings["head"]]
        # self.couplings["head"].exchange()

        # we cannot set the timestep (yet) in Modflow
        # -> set to the (dummy) value 0.0 for now
        self.mf6.prepare_time_step(0.0)
        self.delt = self.mf6.get_time_step()
        self.msw.prepare_time_step(self.delt)

        # convergence loop
        self.mf6.prepare_solve(1)
        for kiter in range(1, self.mf6.max_iter() + 1):
            has_converged = self.do_iter(1)
            if has_converged:
                logger.debug(f"MF6-MSW converged in {kiter} iterations")
                break
        self.mf6.finalize_solve(1)

        self.mf6.finalize_time_step()
        self.msw.finalize_time_step()
        self.log_exchanges()

    def log_exchanges(self) -> None:
        # log per exchange type, per underlying gw-models 
        for exchange_loggers in self.couplings.values():
            [exchange_logger.log(self.get_current_time()) for exchange_logger in exchange_loggers if exchange_logger is not None]

    def finalize(self) -> None:
        self.mf6.finalize()
        self.msw.finalize()
        for exchange_loggers in self.couplings.values():
            [exchange_logger.finalize_log() for exchange_logger in exchange_loggers if exchange_logger is not None]

    def get_current_time(self) -> float:
        return self.mf6.get_current_time()

    def get_end_time(self) -> float:
        return self.mf6.get_end_time()

    def do_iter(self, sol_id: int) -> bool:
        """Execute a single iteration"""
        self.msw.prepare_solve(0)
        self.msw.solve(0)
        [storage.exchange() for storage in self.couplings["storage"]]
        [recharge.exchange(self.delt) for recharge in self.couplings["recharge"]]
        [sprinkling.exchange(self.delt) for sprinkling in self.couplings["sprinkling"] if sprinkling is not None ]
        has_converged = self.mf6.solve(sol_id)
        [head.exchange() for head in self.couplings["head"]]
        self.msw.finalize_solve(0)
        return has_converged

    def report_timing_totals(self) -> None:
        total_mf6 = self.mf6.report_timing_totals()
        total_msw = self.msw.report_timing_totals()
        total = total_mf6 + total_msw
        logger.info(f"Total elapsed time in numerical kernels: {total:0.4f} seconds")
