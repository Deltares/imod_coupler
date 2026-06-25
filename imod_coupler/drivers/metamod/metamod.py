"""MetaMod: the coupling between MetaSWAP and MODFLOW 6

description:

"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from numpy.typing import NDArray

from imod_coupler.config import BaseConfig
from imod_coupler.drivers.driver import Driver
from imod_coupler.drivers.metamod.config import Coupling, MetaModConfig
from imod_coupler.drivers.metamod.utils import (
    CoupledPhreaticHeads,
    CoupledPhreaticRecharge,
    CoupledPhreaticStorage,
)
from imod_coupler.kernelwrappers.mf6_wrapper import Mf6Wrapper
from imod_coupler.kernelwrappers.msw_wrapper import MswMultiWrapper
from imod_coupler.logging.exchange_collector import ExchangeCollector
from imod_coupler.utils import MemoryExchange

from mpi4py import MPI
import sys


class MetaMod(Driver):
    """The driver coupling MetaSWAP and MODFLOW 6"""

    base_config: BaseConfig  # the parsed information from the configuration file
    metamod_config: MetaModConfig  # the parsed information from the configuration file specific to MetaMod

    mpi_comm: MPI.Intracomm
    mpi_size: int
    mpi_rank: int

    timing: bool  # true, when timing is enabled
    mf6: Mf6Wrapper  # the MODFLOW 6 XMI kernel
    msw: MswMultiWrapper  # the MetaSWAP XMI kernel

    delt: float  # time step from MODFLOW 6 (leading)

    enable_sprinkling_groundwater: bool = False

    couplings: dict[
        str, list[Any]  # TODO
    ] = {"storage": [], "recharge": [], "head": [], "sprinkling": []}

    def __init__(self, base_config: BaseConfig, metamod_config: MetaModConfig):
        """Constructs the `MetaMod` object"""
        self.base_config = base_config
        self.mpi_comm = MPI.COMM_WORLD
        if base_config.parallel:
            self.mpi_size = self.mpi_comm.Get_size()
            self.mpi_rank = self.mpi_comm.Get_rank()

            #            if self.mpi_size < 2:
            #                raise ValueError("Number of MPI processes should be > 1.")
            msw_kernels_all = metamod_config.kernels.metaswap
            msw_kernels = []
            msw_models = []
            for kernel in msw_kernels_all:
                if kernel.mpi_rank == self.mpi_rank:
                    msw_kernels.append(kernel)
                    msw_models.append(kernel.msw_model)

            metamod_config.kernels.metaswap = msw_kernels
            self.metamod_config = metamod_config

            couplings_all = metamod_config.coupling
            couplings = []
            for coupling in couplings_all:
                # Fow now, only check for presence of MetaSWAP. FUTURE: include MODFLOW
                if coupling.msw_model in msw_models:
                    couplings.append(coupling)

            self.coupling_configs = couplings
        else:
            self.mpi_size = 1
            self.mpi_rank = 0
            self.metamod_config = metamod_config
            self.coupling_configs = metamod_config.coupling

    def initialize(self) -> None:
        self.mf6 = Mf6Wrapper(
            lib_path=self.metamod_config.kernels.modflow6.dll,
            lib_dependency=self.metamod_config.kernels.modflow6.dll_dep_dir,
            working_directory=self.metamod_config.kernels.modflow6.work_dir,
            timing=self.base_config.timing,
        )
        self.msw = MswMultiWrapper(
            msw_kernels=self.metamod_config.kernels.metaswap,
            timing=self.base_config.timing,
        )

        # Print output to stdout
        self.mf6.set_int("ISTDOUTTOFILE", 0)
        if self.mpi_size > 1:
            comm_f90 = self.mpi_comm.py2f()
            self.mf6.initialize_mpi(comm_f90)
        else:
            self.mf6.initialize()
        for coupling in self.coupling_configs:
            self.mf6.set_head(coupling.mf6_model)
        self.msw.initialize()
        self.initialize_couplings()
        self.log_version()

    def initialize_exchange_logger_per_gwf_model(
        self, output_config_file: Path | None
    ) -> ExchangeCollector:
        if output_config_file is not None:
            exchange_logger = ExchangeCollector.from_file(output_config_file)

        else:
            exchange_logger = ExchangeCollector()
        return exchange_logger

    def get_coupling_tables_per_gwf_model(
        self,
        mf6_msw_node_map: Path,
        mf6_msw_recharge_map: Path,
        msw_model: str,
        mf6_msw_sprinkling_map_groundwater: Path | None,
    ) -> dict[str, NDArray[np.int32]]:
        def svats2index(
            svat: NDArray[np.int32], svat_layer: NDArray[np.int32]
        ) -> NDArray[np.int32]:
            return np.array(
                [svat_lookup[svat[ii], svat_layer[ii]] for ii in range(len(svat))],
                dtype=np.int32,
            )

        # create a lookup, with the svat tuples (id, lay) as keys and the
        # metaswap internal indexes as values
        svat_lookup: dict[tuple[np.int32, np.int32], int] = {}
        msw_mod2svat_file = Path(self.msw.working_dirs[msw_model]) / "mod2svat.inp"
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

        coupling_tables: dict[str, NDArray[np.int32]] = {}
        gwf_table = np.loadtxt(mf6_msw_node_map, dtype=np.int32, ndmin=2)
        coupling_tables["mf6_gwf_nodes"] = (
            gwf_table[:, 0] - 1
        )  # mf6 nodes are one based
        coupling_tables["msw_gwf_nodes"] = svats2index(gwf_table[:, 1], gwf_table[:, 2])

        rch_table: NDArray[np.int32] = np.loadtxt(
            mf6_msw_recharge_map, dtype=np.int32, ndmin=2
        )
        coupling_tables["mf6_rch_nodes"] = rch_table[:, 0] - 1
        coupling_tables["msw_rch_nodes"] = svats2index(rch_table[:, 1], rch_table[:, 2])
        if mf6_msw_sprinkling_map_groundwater is not None:
            well_table: NDArray[np.int32] = np.loadtxt(
                mf6_msw_sprinkling_map_groundwater,
                dtype=np.int32,
                ndmin=2,
            )
            coupling_tables["mf6_well_nodes"] = well_table[:, 0] - 1
            coupling_tables["msw_well_nodes"] = svats2index(
                well_table[:, 1], well_table[:, 2]
            )
            self.enable_sprinkling_groundwater = True
        return coupling_tables

    def initialize_couplings_per_gwf_model(
        self,
        coupled_nodes: dict[str, NDArray[np.int32]],
        exchange_logger: ExchangeCollector,
        mf6_model: str,
        mf6_msw_recharge_pkg: str,
        mf6_msw_well_pkg: str | None,
        msw_model: str,
        coupling_config: Coupling,
    ) -> dict[str, MemoryExchange]:
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
        couplings: dict[str, Any]
        couplings = {
            "storage": MemoryExchange(
                self.msw.get_storage_ptr(msw_model),
                self.mf6.get_storage(mf6_model),
                coupled_nodes["msw_gwf_nodes"],
                coupled_nodes["mf6_gwf_nodes"],
                exchange_logger,
                "storage",
                ptr_b_conversion=conversion_terms_storage,
            ),
            "recharge": MemoryExchange(
                self.msw.get_volume_ptr(msw_model),
                self.mf6.get_recharge(
                    mf6_model,
                    mf6_msw_recharge_pkg,
                ),
                coupled_nodes["msw_rch_nodes"],
                coupled_nodes["mf6_rch_nodes"],
                exchange_logger,
                "recharge",
                ptr_b_conversion=conversion_terms_recharge_area,
            ),
            "head": MemoryExchange(
                self.mf6.head[mf6_model],
                self.msw.get_head_ptr(msw_model),
                coupled_nodes["mf6_gwf_nodes"],
                coupled_nodes["msw_gwf_nodes"],
                exchange_logger,
                "head",
                exchange_operator="avg",
            ),
        }
        if mf6_msw_well_pkg is not None:
            assert isinstance(mf6_msw_well_pkg, str)
            couplings["sprinkling"] = MemoryExchange(
                self.msw.get_volume_ptr(msw_model),
                self.mf6.get_well(
                    mf6_model,
                    mf6_msw_well_pkg,
                ),
                coupled_nodes["msw_well_nodes"],
                coupled_nodes["mf6_well_nodes"],
                exchange_logger,
                "sprinkling",
                exchange_operator="sum",
            )
            self.enable_sprinkling_groundwater = True
        return couplings

    def initialize_couplings(self) -> None:
        # initialize couplings for all gwf-models
        for coupling_config in self.coupling_configs:
            gwf_model = coupling_config.mf6_model
            msw_model = coupling_config.msw_model
            coupled_nodes = self.get_coupling_tables_per_gwf_model(
                coupling_config.mf6_msw_node_map,
                coupling_config.mf6_msw_recharge_map,
                msw_model,
                coupling_config.mf6_msw_sprinkling_map_groundwater,
            )
            exchange_logger = self.initialize_exchange_logger_per_gwf_model(
                coupling_config.output_config_file
            )
            couplings = self.initialize_couplings_per_gwf_model(
                coupled_nodes,
                exchange_logger,
                gwf_model,
                coupling_config.mf6_msw_recharge_pkg,
                coupling_config.mf6_msw_well_pkg,
                msw_model,
                coupling_config,
            )
            # append to list of gwf-model exchanges per exchange type
            for coupling in self.couplings.keys():
                if coupling in couplings:
                    self.couplings[coupling].append(couplings[coupling])

    def log_version(self) -> None:
        logger.info(f"MODFLOW version: {self.mf6.get_version()}")
        logger.info(f"MetaSWAP version: {self.msw.get_version()}")

    def update(self) -> None:
        # heads to MetaSWAP for all coupled gwf-models
        for head_per_gwf_model in self.couplings["head"]:
            head_per_gwf_model.exchange()

        # we cannot set the timestep (yet) in Modflow
        # -> set to the (dummy) value 0.0 for now
        self.mf6.prepare_time_step(0.0)
        self.delt = self.mf6.get_time_step()
        self.msw.prepare_time_step(self.delt)

        # convergence loop
        self.mf6.prepare_solve(1)
        for kiter in range(1, self.mf6.max_iter + 1):
            has_converged = self.do_iter(1)
            if has_converged:
                logger.debug(f"coupled simulation converged in {kiter} iterations")
                break
        if not has_converged:
            if self.mf6.continue_solve:
                logger.warning(
                    "coupled simulation did not converge; mf6 continue = true, continue simulation"
                )
            else:
                raise RuntimeError(
                    "coupled simulation did not converge; mf6 continue = false, stop simulation"
                )
        self.mf6.finalize_solve(1)
        self.mf6.finalize_time_step()
        self.msw.finalize_time_step()
        self.log_exchanges()

    def log_exchanges(self) -> None:
        # log per exchange type, per underlying gw-models
        for exchange_loggers in self.couplings.values():
            for exchange_logger in exchange_loggers:
                if exchange_logger is not None:
                    exchange_logger.log(self.delt)

    def finalize(self) -> None:
        self.mf6.finalize()
        self.msw.finalize()
        for exchange_loggers in self.couplings.values():
            for exchange_logger in exchange_loggers:
                if exchange_logger is not None:
                    exchange_logger.finalize_log()

    def get_current_time(self) -> float:
        sys.stdout.flush()
        return self.mf6.get_current_time()

    def get_end_time(self) -> float:
        sys.stdout.flush()
        return self.mf6.get_end_time()

    def do_iter(self, sol_id: int) -> bool:
        """Execute a single iteration"""
        self.msw.prepare_solve(0)
        self.msw.solve(0)
        for storage_per_gwf_model in self.couplings["storage"]:
            storage_per_gwf_model.exchange()
        for recharge_per_gwf_model in self.couplings["recharge"]:
            recharge_per_gwf_model.exchange()
        if self.enable_sprinkling_groundwater:
            for sprinkling_per_gwf_model in self.couplings["sprinkling"]:
                sprinkling_per_gwf_model.exchange()
        has_converged = self.mf6.solve(sol_id)
        for head_per_gwf_model in self.couplings["head"]:
            head_per_gwf_model.exchange()
        self.msw.finalize_solve(0)
        return has_converged

    def report_timing_totals(self) -> None:
        total_mf6 = self.mf6.report_timing_totals()
        total_msw = self.msw.report_timing_totals()
        total = total_mf6 + total_msw
        logger.info(f"Total elapsed time in numerical kernels: {total:0.4f} seconds")


class MetaModNewton(MetaMod):
    """
    MetaModNewton: the coupling between MetaSWAP and MODFLOW 6, for the Newton formulation of MODFLOW 6
    """

    uzf_active: bool = True
    max_layer_idx: NDArray[np.int32]

    def __init__(self, base_config: BaseConfig, metamod_config: MetaModConfig):
        super().__init__(base_config, metamod_config)

    def initialize_couplings_per_gwf_model(
        self,
        coupled_nodes: dict[str, NDArray[np.int32]],
        exchange_logger: ExchangeCollector,
        mf6_model: str,
        mf6_msw_recharge_pkg: str,
        mf6_msw_well_pkg: str | None,
        msw_model: str,
        coupling_config: Coupling,
    ) -> dict[str, MemoryExchange]:

        # get conversion terms
        mf6_area = self.mf6.get_area(mf6_model)
        conversion_terms_sy = 1.0 / mf6_area
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
        # get aditional info
        first_layer_node_idx = self.get_first_layer_node_idx(
            coupled_nodes["mf6_gwf_nodes"],
            mf6_model,
        )
        userid = self.mf6_get_userid(mf6_model) - 1
        saturation = self.mf6.get_saturation(mf6_model)
        sy = self.mf6.get_sy(mf6_model)
        ss = self.mf6.get_ss(mf6_model)
        nlay, nrow, ncol = self.mf6.get_dis_shape(mf6_model)
        max_layer_idx = self.get_max_layer_idx(coupled_nodes, nlay, coupling_config)
        # fill dictionary of couplings
        couplings: dict[str, Any]
        couplings = {
            "storage": CoupledPhreaticStorage(
                shape=(nlay, nrow, ncol),
                userid=userid,
                ptr_saturation=saturation,
                ptr_storage_sy=sy,
                ptr_storage_ss=ss,
                active_top_layer_nodes=first_layer_node_idx,
                max_layer=max_layer_idx,
                coupling=MemoryExchange(
                    self.msw.get_storage_ptr(mf6_model),
                    np.full_like(first_layer_node_idx, 0.0, dtype=np.float64),
                    coupled_nodes["msw_gwf_nodes"],
                    coupled_nodes["mf6_gwf_nodes"],
                    exchange_logger,
                    "sy",
                    ptr_b_conversion=conversion_terms_sy[first_layer_node_idx],
                ),
            ),
            "recharge": CoupledPhreaticRecharge(
                shape=(nlay, nrow, ncol),
                userid=userid,
                ptr_saturation=saturation,
                ptr_recharge=self.mf6.get_recharge(
                    mf6_model,
                    mf6_msw_recharge_pkg,
                ),
                ptr_recharge_nodelist=self.mf6.get_recharge_nodes(
                    mf6_model,
                    mf6_msw_recharge_pkg,
                ),
                max_layer=max_layer_idx,
                coupling=MemoryExchange(
                    self.msw.get_volume_ptr(msw_model),
                    self.mf6.get_recharge(
                        mf6_model,
                        mf6_msw_recharge_pkg,
                    ),
                    coupled_nodes["msw_rch_nodes"],
                    coupled_nodes["mf6_rch_nodes"],
                    exchange_logger,
                    "recharge",
                    ptr_b_conversion=conversion_terms_recharge_area,
                ),
            ),
            "head": CoupledPhreaticHeads(
                shape=(nlay, nrow, ncol),
                userid=userid,
                ptr_saturation=saturation,
                ptr_heads=self.mf6.head[mf6_model],
                active_top_layer_nodes=first_layer_node_idx,
                max_layer=max_layer_idx,
                coupling=MemoryExchange(
                    np.full_like(first_layer_node_idx, 0.0, dtype=np.float64),
                    self.msw.get_head_ptr(msw_model),
                    coupled_nodes["mf6_gwf_nodes"],
                    coupled_nodes["msw_gwf_nodes"],
                    exchange_logger,
                    "head",
                    exchange_operator="avg",
                ),
            ),
        }
        if self.enable_sprinkling_groundwater:
            assert isinstance(mf6_msw_well_pkg, str)
            couplings["sprinkling"] = MemoryExchange(
                self.msw.get_volume_ptr(msw_model),
                self.mf6.get_well(
                    mf6_model,
                    mf6_msw_well_pkg,
                ),
                coupled_nodes["msw_well_nodes"],
                coupled_nodes["mf6_well_nodes"],
                exchange_logger,
                "sprinkling",
                exchange_operator="sum",
            )
            self.enable_sprinkling_groundwater = True
        return couplings

    def get_first_layer_node_idx(
        self, node_idx: NDArray[Any], mf6_model: str
    ) -> NDArray[np.int32]:
        _, nrow, ncol = self.mf6.get_dis_shape(mf6_model)
        userid = self.mf6_get_userid(mf6_model)
        first_layer_ids = userid[userid <= (nrow * ncol)]
        if node_idx.max() > first_layer_ids.max():
            raise ValueError(
                "MetaSWAP can only be coupled to the first model layer of MODFLOW 6"
            )
        return first_layer_ids - 1

    def mf6_get_userid(self, mf6_model: str) -> NDArray[np.int32]:
        nlay, nrow, ncol = self.mf6.get_dis_shape(mf6_model)
        userid = self.mf6.get_nodeuser(mf6_model)
        if userid.size == 1:
            # no reduced domain, set userid to modelid
            # TODO: find out if there is a flag that indicates that usernodes == modelnodes
            userid = np.arange(nlay * nrow * ncol, dtype=np.int32)
        return userid

    def get_max_layer_idx(
        self,
        coupled_nodes: dict[str, NDArray[np.int32]],
        nlay: int,
        coupling_config: Coupling,
    ) -> NDArray[np.int32]:
        if coupling_config.mf6_node_max_layer is not None:
            table_node_layer: NDArray[np.int32] = np.loadtxt(
                coupling_config.mf6_node_max_layer,
                dtype=np.int64,
                ndmin=2,
                skiprows=1,
            )
            return table_node_layer[:, 1] - 1
        else:
            return np.full_like(
                coupled_nodes["mf6_gwf_nodes"], fill_value=nlay - 1, dtype=np.int32
            )
