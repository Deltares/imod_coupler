"""MetaMod: the coupling between MetaSWAP and MODFLOW 6

description:

"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from numpy.typing import NDArray

from imod_coupler.config import BaseConfig
from imod_coupler.drivers.driver import Driver
from imod_coupler.drivers.metamod.config import MetaModConfig
from imod_coupler.drivers.metamod.utils import (
    CoupledPhreaticHeads,
    CoupledPhreaticRecharge,
    CoupledPhreaticStorage,
    CoupledUZF,
)
from imod_coupler.kernelwrappers.mf6_wrapper import Mf6Wrapper
from imod_coupler.kernelwrappers.msw_wrapper import MswWrapper
from imod_coupler.logging.exchange_collector import ExchangeCollector
from imod_coupler.utils import MemoryExchange


class MetaMod(Driver):
    """The driver coupling MetaSWAP and MODFLOW 6"""

    base_config: BaseConfig  # the parsed information from the configuration file
    metamod_config: MetaModConfig  # the parsed information from the configuration file specific to MetaMod

    timing: bool  # true, when timing is enabled
    mf6: Mf6Wrapper  # the MODFLOW 6 XMI kernel
    msw: MswWrapper  # the MetaSWAP XMI kernel

    max_iter: NDArray[Any]  # max. nr outer iterations in MODFLOW kernel
    delt: float  # time step from MODFLOW 6 (leading)
    iter_debug: float = 0.0
    enable_sprinkling_groundwater: bool = False
    simulation_time: float = 0.0  # for ATS

    couplings: dict[
        str,
        MemoryExchange
        | CoupledPhreaticStorage
        | CoupledPhreaticRecharge
        | CoupledPhreaticHeads
        | CoupledUZF,
    ]

    def __init__(self, base_config: BaseConfig, metamod_config: MetaModConfig):
        """Constructs the `MetaMod` object"""
        self.base_config = base_config
        self.metamod_config = metamod_config
        self.coupling_config = metamod_config.coupling[
            0
        ]  # Adapt as soon as we have multimodel support

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
        self.log_version()
        self.set_coupling()
        self.mf6.set_ats_package()  # should be optional together with the msw save state logic

    def get_exchange_logger(self) -> ExchangeCollector:
        if self.coupling_config.output_config_file is not None:
            exchange_logger = ExchangeCollector.from_file(
                self.coupling_config.output_config_file
            )
        else:
            exchange_logger = ExchangeCollector()
        return exchange_logger

    def get_coupled_nodes(
        self,
        mf6_msw_node_map: Path,
        mf6_msw_recharge_map: Path,
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

    def set_coupling(self) -> None:
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

        # get coupled indexes
        coupled_nodes = self.get_coupled_nodes(
            self.coupling_config.mf6_msw_node_map,
            self.coupling_config.mf6_msw_recharge_map,
            self.coupling_config.mf6_msw_sprinkling_map_groundwater,
        )

        # get exchange logger
        exchange_logger = self.get_exchange_logger()
        # set couplings
        self.couplings = {
            "storage": MemoryExchange(
                self.msw.get_storage_ptr(),
                self.mf6.get_storage(self.coupling_config.mf6_model),
                coupled_nodes["msw_gwf_nodes"],
                coupled_nodes["mf6_gwf_nodes"],
                exchange_logger,
                "storage",
                ptr_b_conversion=conversion_terms_storage,
            ),
            "recharge": MemoryExchange(
                self.msw.get_volume_ptr(),
                self.mf6.get_recharge(
                    self.coupling_config.mf6_model,
                    self.coupling_config.mf6_msw_recharge_pkg,
                ),
                coupled_nodes["msw_rch_nodes"],
                coupled_nodes["mf6_rch_nodes"],
                exchange_logger,
                "recharge",
                ptr_b_conversion=conversion_terms_recharge_area,
            ),
            "head": MemoryExchange(
                self.mf6.get_head(self.coupling_config.mf6_model),
                self.msw.get_head_ptr(),
                coupled_nodes["mf6_gwf_nodes"],
                coupled_nodes["msw_gwf_nodes"],
                exchange_logger,
                "head",
                exchange_operator="avg",
            ),
        }
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
                exchange_logger,
                "sprinkling",
                exchange_operator="sum",
            )
            self.enable_sprinkling_groundwater = True

    def log_version(self) -> None:
        logger.info(f"MODFLOW version: {self.mf6.get_version()}")
        logger.info(f"MetaSWAP version: {self.msw.get_version()}")

    def update(self) -> None:
        # heads to MetaSWAP
        self.couplings["head"].exchange()
        # save the MetaSWAP state
        self.msw_save_state()

        # reset
        self.mf6.ats.prepare()

        self.mf6.prepare_time_step(0.0)
        for attempt in range(10):  # max 10 retry attempts
            # heads to MetaSWAP
            self.couplings["head"].exchange()
            self.delt = self.mf6.get_time_step()
            self.msw.prepare_time_step(self.delt)
            converged = self.do_solve()
            if converged or not self.mf6.ats.should_retry():
                break
            self.mf6.ats.retry()
            self.msw_restore_state()
        self.mf6.finalize_time_step()
        self.msw.finalize_time_step()

    def do_solve(self) -> bool:
        self.mf6.prepare_solve(1)
        for kiter in range(1, self.mf6.max_iter() + 1):
            has_converged = self.do_iter(kiter)
            self.log_exchanges()
            self.iter_debug += 1.0
            if has_converged:
                logger.debug(f"MF6-MSW converged in {kiter} iterations")
                break
        logger.info(f"has converged: {has_converged}")
        self.mf6.finalize_solve(1)
        return has_converged

    def log_exchanges(self) -> None:
        for coupling in self.couplings.values():
            coupling.log(
                self.iter_debug,  # self.get_current_time()
            )

    def finalize(self) -> None:
        self.mf6.finalize()
        self.msw.finalize()
        for coupling in self.couplings.values():
            coupling.finalize_log()

    def get_current_time(self) -> float:
        return self.mf6.get_current_time()

    def get_end_time(self) -> float:
        return self.mf6.get_end_time()

    def do_iter(self, sol_id: int) -> bool:
        """Execute a single iteration"""
        self.msw.prepare_solve(0)
        self.msw.solve(0)
        self.couplings["storage"].exchange()
        self.couplings["recharge"].exchange(self.delt)
        if self.enable_sprinkling_groundwater:
            self.couplings["sprinkling"].exchange(self.delt)
        has_converged = self.mf6.solve(1)
        self.couplings["head"].exchange()
        self.msw.finalize_solve(0)
        return has_converged

    def report_timing_totals(self) -> None:
        total_mf6 = self.mf6.report_timing_totals()
        total_msw = self.msw.report_timing_totals()
        total = total_mf6 + total_msw
        logger.info(f"Total elapsed time in numerical kernels: {total:0.4f} seconds")

    def msw_restore_state(self) -> None:
        path_org = os.getcwd()
        os.chdir(path_org + "/MetaSWAP")
        self.msw.restore_state()
        os.chdir(path_org)
        self.simulation_time = np.copy(self.mf6.get_current_time())

    def msw_save_state(self) -> None:
        self.msw.save_state()


class MetaModNewton(MetaMod):
    """
    MetaModNewton: the coupling between MetaSWAP and MODFLOW 6, for the Newton formulation of MODFLOW 6
    """

    uzf_active: bool = False
    max_layer_idx: NDArray[np.int32]

    def __init__(self, base_config: BaseConfig, metamod_config: MetaModConfig):
        super().__init__(base_config, metamod_config)

    def set_coupling(self) -> None:
        # get coupled indexes
        coupled_nodes = self.get_coupled_nodes(
            self.coupling_config.mf6_msw_node_map,
            self.coupling_config.mf6_msw_recharge_map,
            self.coupling_config.mf6_msw_sprinkling_map_groundwater,
        )
        # get exchange logger
        exchange_logger = self.get_exchange_logger()
        # get conversion terms
        mf6_area = self.mf6.get_area(self.coupling_config.mf6_model)
        conversion_terms_sy = 1.0 / mf6_area
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
        # get aditional info
        first_layer_node_idx = self.get_first_layer_user_idx(
            coupled_nodes["mf6_gwf_nodes"]
        )
        userid = self.mf6_get_userid() - 1
        saturation = self.mf6.get_saturation(self.coupling_config.mf6_model)
        sy = self.mf6.get_sy(self.coupling_config.mf6_model)
        ss = self.mf6.get_ss(self.coupling_config.mf6_model)
        nlay, nrow, ncol = self.mf6.get_dis_shape(self.coupling_config.mf6_model)
        max_layer_idx = self.get_max_layer_idx(first_layer_node_idx, nlay)
        self.uzf_active = self.coupling_config.mf6_uzf_pkg is not None
        # fill dictionary of couplings
        self.couplings = {
            "storage": CoupledPhreaticStorage(
                shape=(nlay, nrow, ncol),
                userid=userid,
                ptr_saturation=saturation,
                ptr_storage_sy=sy,
                ptr_storage_ss=ss,
                active_top_layer_nodes=first_layer_node_idx,
                coupled_top_layer_nodes=np.unique(coupled_nodes["mf6_gwf_nodes"]),
                max_layer=max_layer_idx,
                coupling=MemoryExchange(
                    self.msw.get_storage_ptr(),
                    np.full_like(first_layer_node_idx, 0.0, dtype=np.float64),
                    coupled_nodes["msw_gwf_nodes"],
                    coupled_nodes["mf6_gwf_nodes"],  #
                    exchange_logger,
                    "sy",
                    ptr_a_conversion=conversion_terms_sy[
                        coupled_nodes["mf6_gwf_nodes"]
                    ],
                ),
            ),
            "recharge": CoupledPhreaticRecharge(
                shape=(nlay, nrow, ncol),
                userid=userid,
                ptr_saturation=saturation,
                ptr_recharge=self.mf6.get_recharge(
                    self.coupling_config.mf6_model,
                    self.coupling_config.mf6_msw_recharge_pkg,
                ),
                ptr_recharge_nodelist=self.mf6.get_recharge_nodes(
                    self.coupling_config.mf6_model,
                    self.coupling_config.mf6_msw_recharge_pkg,
                ),
                max_layer=max_layer_idx,
                coupling=MemoryExchange(
                    self.msw.get_volume_ptr(),
                    self.mf6.get_recharge(
                        self.coupling_config.mf6_model,
                        self.coupling_config.mf6_msw_recharge_pkg,
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
                ptr_heads=self.mf6.get_head(self.coupling_config.mf6_model),
                active_top_layer_nodes=first_layer_node_idx,
                max_layer=max_layer_idx,
                coupling=MemoryExchange(
                    np.full_like(first_layer_node_idx, 0.0, dtype=np.float64),
                    self.msw.get_head_ptr(),
                    coupled_nodes["mf6_gwf_nodes"],
                    coupled_nodes["msw_gwf_nodes"],
                    exchange_logger,
                    "head",
                    exchange_operator="avg",
                ),
            ),
        }
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
                exchange_logger,
                "sprinkling",
                exchange_operator="sum",
            )
            self.enable_sprinkling_groundwater = True
        if self.uzf_active:
            self.couplings["uzf"] = CoupledUZF(
                shape=(nlay, nrow, ncol),
                new_recharge=self.mf6.get_recharge(
                    self.coupling_config.mf6_model,
                    self.coupling_config.mf6_msw_recharge_pkg,
                ),
                head=self.mf6.get_head(self.coupling_config.mf6_model),
                infiltration_ptr=self.mf6.get_uzf_infiltration(
                    self.coupling_config.mf6_model, self.coupling_config.mf6_uzf_pkg
                ),
                nodelist_ptr=self.mf6.get_uzf_nodes(
                    self.coupling_config.mf6_model, self.coupling_config.mf6_uzf_pkg
                ),
                userid=userid,
                max_layer_index=self.get_max_layer_idx(nlay),
                first_layer_nodes=self.get_first_layer_user_idx(
                    coupled_nodes["mf6_gwf_nodes"]
                ),
                top=self.mf6.get_uzf_top(
                    self.coupling_config.mf6_model, self.coupling_config.mf6_uzf_pkg
                ),
                landflag=self.mf6.get_uzf_landflag(
                    self.coupling_config.mf6_model, self.coupling_config.mf6_uzf_pkg
                ),
            )

    def do_iter(self, sol_id: int) -> bool:
        """Execute a single iteration"""
        self.msw.prepare_solve(0)
        self.msw.solve(0)
        self.couplings["storage"].exchange()
        if self.uzf_active:
            self.couplings["uzf"].exchange(self.delt)
        self.couplings["recharge"].exchange(self.delt)
        if self.enable_sprinkling_groundwater:
            self.couplings["sprinkling"].exchange(self.delt)
        has_converged = self.mf6.solve(1)
        self.couplings["head"].exchange()
        self.msw.finalize_solve(0)
        return has_converged

    def get_first_layer_user_idx(
        self, node_idx: NDArray[np.int32]
    ) -> NDArray[np.int32]:
        """
        MF6 nodes reduced layer 1:       |    |    |  1  |  2  |  3   |  4   |
        MF6 nodes userid's layer 1:      |  1 |  2 |  3  |  4  |  5   |  6   |

        MSW nodes subunit 1:             |    |    |     |     |  1   |  2   |
        MSW nodes subunit 2:             |    |    |     |  3  |  4   |  5   |

        firsts_layer_user_idx = [1, 2, 3, 4]
        Get the user defined first layer indexes for couped elements"""
        _, nrow, ncol = self.mf6.get_dis_shape(self.coupling_config.mf6_model)
        userid = self.mf6_get_userid()
        first_layer_ids = userid[userid <= (nrow * ncol)]
        if node_idx.max() > first_layer_ids.max():
            raise ValueError(
                "MetaSWAP can only be coupled to the first model layer of MODFLOW 6"
            )
        return first_layer_ids - 1

    def mf6_get_userid(self) -> NDArray[np.int32]:
        nlay, nrow, ncol = self.mf6.get_dis_shape(self.coupling_config.mf6_model)
        userid = self.mf6.get_nodeuser(self.coupling_config.mf6_model)
        if userid.size == 1:
            # no reduced domain, set userid to modelid
            # TODO: find out if there is a flag that indicates that usernodes == modelnodes
            userid = np.arange(nlay * nrow * ncol)
        return userid

    def get_max_layer_idx(
        self, first_layer_node_idx: NDArray[np.int32], nlay
    ) -> NDArray[np.int32]:
        table_node_layer = np.array([0])
        if self.coupling_config.mf6_node_max_layer is not None:
            table_node_layer: NDArray[np.int32] = np.loadtxt(
                self.coupling_config.mf6_node_max_layer,
                dtype=np.int64,
                ndmin=2,
                skiprows=1,
            )
        else:
            return np.full_like(first_layer_node_idx, nlay, dtype=np.int32)
        # phreatic mapping is done based on all first layer nodes,
        # broadcast to this shape so it can be used in max/min array operation
        max_layer_idx = table_node_layer[:, 1] - 1
        nodes_idx = table_node_layer[:, 0] - 1
        broadcast = np.full_like(first_layer_node_idx, max_layer_idx.max())
        broadcast[nodes_idx] = max_layer_idx
        return broadcast

    def get_bottom_coupled_nodes(self, layers, node_indx) -> NDArray[Any]:
        nlay, nrow, ncol = self.mf6.get_dis_shape(self.coupling.mf6_model)
        userid = self.mf6_get_userid()
        bottom_nodes = np.full(nlay * nrow * ncol, np.nan, dtype=np.float64)
        bottom_nodes[userid - 1] = self.mf6.get_bot(self.coupling.mf6_model)
        bottom_nodes = bottom_nodes.reshape((nlay, nrow * ncol))
        return bottom_nodes[layers - 1, userid[node_indx] - 1]
