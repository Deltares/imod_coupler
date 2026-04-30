"""MegaMod: the coupling between MegaSWAP and MODFLOW 6

description:

"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from numpy.typing import NDArray
from scipy.sparse import csr_matrix, dia_matrix

from imod_coupler.config import BaseConfig
from imod_coupler.drivers.driver import Driver
from imod_coupler.drivers.megamod.config import Coupling, MegaModConfig
from imod_coupler.kernelwrappers.mf6_wrapper import Mf6Wrapper
#from imod_coupler.logging.exchange_collector import ExchangeCollector
from imod_coupler.utils import create_mapping
from xmipy import XmiWrapper
from imod_coupler.drivers.megamod.logging import Logging

class MegaMod(Driver):
    """The driver coupling MegaSWAP and MODFLOW 6"""

    base_config: BaseConfig  # the parsed information from the configuration file
    coupling: Coupling  # the coupling information

    timing: bool  # true, when timing is enabled
    logging: Logging
    mf6: Mf6Wrapper  # the MODFLOW 6 XMI kernel
    msw: XmiWrapper  # the MegaSWAP XMI kernel

    max_iter: NDArray[Any]  # max. nr outer iterations in MODFLOW kernel
    delt: float  # time step from MODFLOW 6 (leading)

    mf6_head: NDArray[Any]  # the hydraulic head array in the coupled model
    mf6_recharge: NDArray[np.float64]  # the coupled recharge array from the RCH package
    mf6_storage: NDArray[Any]  # the specific storage array (ss)
    mf6_has_sc1: bool  # when true, specific storage in mf6 is given as a storage coefficient (sc1)
    mf6_area: NDArray[Any]  # cell area (size:nodes)
    mf6_top: NDArray[Any]  # top of cell (size:nodes)
    mf6_bot: NDArray[Any]  # bottom of cell (size:nodes)

    mf6_sprinkling_wells: NDArray[Any]  # the well data for coupled extractions
    msw_head: NDArray[Any]  # internal MetaSWAP groundwater head
    msw_volume: NDArray[Any]  # unsaturated zone flux (as a volume!)
    msw_storage: NDArray[Any]  # MetaSWAP storage coefficients (MODFLOW's sc1)

    enable_sprinkling_groundwater: bool
    # dictionary with mapping tables for mod=>msw coupling
    map_mod2msw: dict[str, csr_matrix] = {}
    # dictionary with mapping tables for msw=>mod coupling
    map_msw2mod: dict[str, csr_matrix] = {}
    # dict. with mask arrays for mod=>msw coupling
    mask_mod2msw: dict[str, NDArray[Any]] = {}
    # dict. with mask arrays for msw=>mod coupling
    mask_msw2mod: dict[str, NDArray[Any]] = {}

    def __init__(self, base_config: BaseConfig, megamod_config: MegaModConfig):
        """Constructs the `MetaMod` object"""
        self.base_config = base_config
        self.megamod_config = megamod_config
        self.coupling = megamod_config.coupling[
            0
        ]  # Adapt as soon as we have multimodel support
        self.logging = Logging()

    def initialize(self) -> None:
        self.mf6 = Mf6Wrapper(
            lib_path=self.megamod_config.kernels.modflow6.dll,
            lib_dependency=self.megamod_config.kernels.modflow6.dll_dep_dir,
            working_directory=self.megamod_config.kernels.modflow6.work_dir,
            timing=self.base_config.timing,
        )
        self.msw = XmiWrapper(
            lib_path=self.megamod_config.kernels.megaswap.dll,
            lib_dependency=self.megamod_config.kernels.megaswap.dll_dep_dir,
            working_directory=self.megamod_config.kernels.megaswap.work_dir,
            timing=self.base_config.timing,
        )
        # Print output to stdout
        self.mf6.set_int("ISTDOUTTOFILE", 0)
        self.mf6.initialize()
        self.msw.initialize()
        self.log_version()
        self.exchange_logger = None
        self.couple()

    def log_version(self) -> None:
        logger.info(f"MODFLOW version: {self.mf6.get_version()}")
        logger.info("MegaSWAP prototype")

    def couple(self) -> None:
        """Couple Modflow and Megaswap"""
        self.mf6_head = self.mf6.get_head(self.coupling.mf6_model)
        self.mf6_head_old = self.mf6.get_head_old(self.coupling.mf6_model)
        self.mf6_recharge = self.mf6.get_recharge(
            self.coupling.mf6_model, self.coupling.mf6_msw_recharge_pkg
        )
        nodelist_address = self.mf6.get_var_address(
            "NODELIST", self.coupling.mf6_model, self.coupling.mf6_msw_recharge_pkg
        )
        self.mf6_recharge_nodelist = self.mf6.get_value_ptr(nodelist_address)
        self.mf6_storage = self.mf6.get_storage(self.coupling.mf6_model)
        self.mf6_has_sc1 = self.mf6.has_sc1(self.coupling.mf6_model)
        self.mf6_area = self.mf6.get_area(self.coupling.mf6_model)
        self.mf6_top = self.mf6.get_top(self.coupling.mf6_model)
        self.mf6_bot = self.mf6.get_bot(self.coupling.mf6_model)
        self.max_iter = self.mf6.max_iter()

        self.msw_nbox = self.msw.get_value_ptr('nbox')
        self.msw_head = self.msw.get_value_ptr('lvgwmodf')
        self.msw_phead = self.msw.get_value_ptr('phead')
        self.msw_volume = self.msw.get_value_ptr('vsim')
        self.msw_storage = self.msw.get_value_ptr('sc1sim')
        self.msw_qmodf = self.msw.get_value_ptr('qmodf')
        self.msw_qrun = self.msw.get_value_ptr('qrun')
        self.msw_evsoil = self.msw.get_value_ptr('evsoil')
        self.msw_evpond = self.msw.get_value_ptr('evpond')
        self.msw_dtgw = self.msw.get_value_ptr('dtgw')
        self.msw_tiop = self.msw.get_value_ptr('tiop')

        # create mappings
        table_node2svat: NDArray[np.int32] = np.loadtxt(
            self.coupling.mf6_msw_node_map, dtype=np.int32, ndmin=2
        )
        node_idx = table_node2svat[:, 0] - 1
        msw_idx = table_node2svat[:, 1] - 1 # we assume no svats vor sprinkling for now

        self.map_msw2mod["storage"], self.mask_msw2mod["storage"] = create_mapping(
            msw_idx,
            node_idx,
            self.msw_storage.size,
            self.mf6_storage.size,
            "sum",
        )

        if self.mf6_has_sc1:
            conversion_terms = np.ones_like(self.mf6_bot)*1.0 
        else:
            conversion_terms = np.ones_like(self.mf6_bot) * 1.0 / (self.mf6_top - self.mf6_bot)

        conversion_matrix = dia_matrix(
            (conversion_terms, [0]),
            shape=(self.mf6_area.size, self.mf6_area.size),
            dtype=self.mf6_area.dtype,
        )
        self.map_msw2mod["storage"] = conversion_matrix * self.map_msw2mod["storage"]

        self.map_mod2msw["head"], self.mask_mod2msw["head"] = create_mapping(
            node_idx,
            msw_idx,
            self.mf6_head.size,
            self.msw_head.size,
            "avg",
        )

        table_rch2svat: NDArray[np.int32] = np.loadtxt(
            self.coupling.mf6_msw_recharge_map, dtype=np.int32, ndmin=2
        )
        rch_idx = table_rch2svat[:, 0] - 1
        msw_idx = table_rch2svat[:, 1] - 1
        self.map_msw2mod["recharge"], self.mask_msw2mod["recharge"] = create_mapping(
            msw_idx,
            rch_idx,
            self.msw_volume.size,
            self.mf6_recharge.size,
            "sum",
        )

    def log_exchange_vars(self, svat, node) -> None:
        self.logging.phead_list.append(list(self.msw_phead[svat,:]))
        self.logging.head_list.append(self.mf6_head[node])
        self.logging.vsim_list.append(self.mf6_recharge[node])
        self.logging.qmodf_list.append(self.msw_qmodf[node])
        self.logging.qrun_list.append(self.msw_qrun[node])
        self.logging.sc1_list.append(self.msw_storage[svat])
        self.logging.nbox_list.append(self.msw_nbox[svat])
        self.logging.evsoil_list.append(self.msw_evsoil[node])
        self.logging.evpond_list.append(self.msw_evpond[node])

    def update(self) -> None:
        print ("============================================")
        print ("mf6-prepare timestep")
        self.mf6.prepare_time_step(0.0)
        self.delt = self.mf6.get_time_step()

        self.exchange_heads_mf2msw()
        print ("exchange head mf to sss")
        # write into the msw pointer if available; preserve fallback to scalar
        try:
            self.msw_tiop[:] = self.get_current_time()
        except Exception:
            self.msw_tiop = self.get_current_time()
        self.msw.prepare_time_step(self.delt)
        self.exchange_sc1_msw2mf()
        self.exchange_recharge_msw2mf()
        print ("exchange sc1 sss to mf")
        print ("exchange recharge sss to mf")

        # convergence loop
        self.mf6.prepare_solve(1)
        for kiter in range(1, self.max_iter + 1):
            print ("===============   Begin Iter")
            has_converged = self.do_iter(1)
            self.fdump.write("%8.3f %15.5e %15.5e %15.5e %15.5e\n"
                         %(self.get_current_time(), self.msw_storage[0],self.msw_volume[0],self.msw_phead[0][0], self.msw_phead[0][1]))
            if has_converged:
                logger.debug(f"MF6-MSW converged in {kiter} iterations")
                break
            print ("===============   End Iter")
        self.fdump.write("%8.3f %15.5e %15.5e %15.5e %15.5e\n"
                         %(self.get_current_time(), self.msw_storage[0],self.msw_volume[0],self.msw_phead[0][0], self.msw_phead[0][1]))
        self.mf6.finalize_solve(1)
        self.mf6.finalize_time_step()
        print ("mf finalize time step")
        self.exchange_qmodf()
        print ("exchange qmodf mf to sss")
        self.log_exchange_vars(0,0)

        self.msw.finalize_time_step() # should compute qmodf intenal?
        print ("============================================")

    def finalize(self) -> None:
        self.mf6.finalize()
        self.msw.finalize()
        if self.exchange_logger is not None:
            self.exchange_logger.finalize()

    def get_current_time(self) -> float:
        tiop = self.mf6.get_current_time()
        return tiop

    def get_end_time(self) -> float:
        return self.mf6.get_end_time()

    def do_iter(self, sol_id: int) -> bool:
        """Execute a single iteration"""
        self.exchange_heads_mf2msw()
        print ("exchange head mf to sss")
        self.msw.solve()
        # TODO: reset qmv in msw
        self.exchange_sc1_msw2mf()
        self.exchange_recharge_msw2mf()
        print ("exchange sc1 sss to mf")
        print ("exchange recharge sss to mf")
        print (np.min(self.mf6_recharge), np.max(self.mf6_recharge))
        has_converged = self.mf6.solve(sol_id)
        print ("mf solve")
        return has_converged

    def report_timing_totals(self) -> None:
        total_mf6 = self.mf6.report_timing_totals()
        total_msw = self.msw.report_timing_totals()
        total = total_mf6 + total_msw
        logger.info(f"Total elapsed time in numerical kernels: {total:0.4f} seconds")

    def exchange_qmodf(self) -> None:
#       self.mf6_qmodf = ((self.mf6_head[:] - self.mf6_head_old[:]) * self.mf6_storage[:]) - self.mf6_recharge[:]
#       self.msw_qmodf[:] = (
#           self.mask_mod2msw["head"][:] * self.msw_qmodf[:]
#           + self.map_mod2msw["head"].dot(self.mf6_qmodf)[:]  
#       )
        self.mf6_qmodf = ((self.mf6_head[:] - self.mf6_head_old[:]) * self.mf6_storage[:])
        self.msw_qmodf[:] = (
            self.mask_mod2msw["head"][:] * self.msw_qmodf[:]
            + self.map_mod2msw["head"].dot(self.mf6_qmodf)[:]  
            - self.msw_volume[:]/self.delt/self.mf6_area[self.mf6_recharge_nodelist - 1]   # recharge term
        )
        return

    def exchange_sc1_msw2mf(self) -> None:
        self.mf6_storage[:] = (
            self.mask_msw2mod["storage"][:] * self.mf6_storage[:]
            + self.map_msw2mod["storage"].dot(self.msw_storage)[:]
        )
        if self.exchange_logger is not None:
            self.exchange_logger.log_exchange(
                "mf6_storage", self.mf6_storage, self.get_current_time()
            )
            self.exchange_logger.log_exchange(
                "msw_storage", self.msw_storage, self.get_current_time()
            )

    def exchange_recharge_msw2mf(self) -> None:
        #TODO: check units
        self.mf6_recharge[:] = (
            self.mask_msw2mod["recharge"][:] * self.mf6_recharge[:]
            + self.map_msw2mod["recharge"].dot(self.msw_volume)[:] / self.delt  
        ) / self.mf6_area[self.mf6_recharge_nodelist - 1]

    def exchange_heads_mf2msw(self) -> None:
        self.msw_head[:] = (
            self.mask_mod2msw["head"][:] * self.msw_head[:]
            + self.map_mod2msw["head"].dot(self.mf6_head)[:]
        )
