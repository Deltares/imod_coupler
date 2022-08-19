""" MetaMod: the coupling between MetaSWAP and MODFLOW 6

description:

"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from pydantic import FilePath
from scipy.sparse import csr_matrix, dia_matrix
from xmipy import XmiWrapper

from imod_coupler.config import BaseConfig
from imod_coupler.drivers.driver import Driver
from imod_coupler.drivers.metamod.config import Coupling, MetaModConfig
from imod_coupler.utils import create_mapping

logger = logging.getLogger(__name__)


class MetaMod(Driver):
    """The driver coupling MetaSWAP and MODFLOW 6"""

    base_config: BaseConfig  # the parsed information from the configuration file
    metamod_config: MetaModConfig  # the parsed information from the configuration file specific to MetaMod
    coupling: Coupling  # the coupling information

    timing: bool  # true, when timing is enabled
    mf6: XmiWrapper  # the MODFLOW 6 XMI kernel
    msw: XmiWrapper  # the MetaSWAP XMI kernel

    max_iter: NDArray[Any]  # max. nr outer iterations in MODFLOW kernel
    delt: float  # time step from MODFLOW 6 (leading)

    mf6_head: NDArray[Any]  # the hydraulic head array in the coupled model
    mf6_recharge: NDArray[Any]  # the coupled recharge array from the RCH package
    mf6_storage: NDArray[Any]  # the specific storage array (ss)
    mf6_has_sc1: bool  # when true, specific storage in mf6 is given as a storage coefficient (sc1)
    mf6_area: NDArray[Any]  # cell area (size:nodes)
    mf6_top: NDArray[Any]  # top of cell (size:nodes)
    mf6_bot: NDArray[Any]  # bottom of cell (size:nodes)

    mf6_sprinkling_wells: NDArray[Any]  # the well data for coupled extractions
    msw_head: NDArray[Any]  # internal MetaSWAP groundwater head
    msw_volume: NDArray[Any]  # unsaturated zone flux (as a volume!)
    msw_storage: NDArray[Any]  # MetaSWAP storage coefficients (MODFLOW's sc1)
    msw_time: float  # MetaSWAP current time

    # dictionary with mapping tables for mod=>msw coupling
    map_mod2msw: dict[str, csr_matrix] = {}
    # dictionary with mapping tables for msw=>mod coupling
    map_msw2mod: dict[str, csr_matrix] = {}
    # dict. with mask arrays for mod=>msw coupling
    mask_mod2msw: dict[str, NDArray[Any]] = {}
    # dict. with mask arrays for msw=>mod coupling
    mask_msw2mod: dict[str, NDArray[Any]] = {}

    def __init__(self, base_config: BaseConfig, metamod_config: MetaModConfig):
        """Constructs the `MetaMod` object"""
        self.base_config = base_config
        self.metamod_config = metamod_config
        self.coupling = metamod_config.coupling[
            0
        ]  # Adapt as soon as we have multimodel support

    def initialize(self) -> None:
        self.mf6 = XmiWrapper(
            lib_path=self.metamod_config.kernels.modflow6.dll,
            lib_dependency=self.metamod_config.kernels.modflow6.dll_dep_dir,
            working_directory=self.metamod_config.kernels.modflow6.work_dir,
            timing=self.base_config.timing,
        )
        self.msw = XmiWrapper(
            lib_path=self.metamod_config.kernels.metaswap.dll,
            lib_dependency=self.metamod_config.kernels.metaswap.dll_dep_dir,
            working_directory=self.metamod_config.kernels.metaswap.work_dir,
            timing=self.base_config.timing,
        )
        # Print output to stdout
        self.mf6.set_int("ISTDOUTTOFILE", 0)
        self.mf6.initialize()
        self.msw.initialize()
        self.couple()

    def couple(self) -> None:
        """Couple Modflow and Metaswap"""
        # get some 'pointers' to MF6 and MSW internal data
        mf6_head_tag = self.mf6.get_var_address("X", self.coupling.mf6_model)
        mf6_recharge_tag = self.mf6.get_var_address(
            "BOUND", self.coupling.mf6_model, self.coupling.mf6_msw_recharge_pkg
        )
        mf6_storage_tag = self.mf6.get_var_address("SS", self.coupling.mf6_model, "STO")
        mf6_is_sc1_tag = self.mf6.get_var_address(
            "ISTOR_COEF", self.coupling.mf6_model, "STO"
        )
        mf6_area_tag = self.mf6.get_var_address("AREA", self.coupling.mf6_model, "DIS")
        mf6_top_tag = self.mf6.get_var_address("TOP", self.coupling.mf6_model, "DIS")
        mf6_bot_tag = self.mf6.get_var_address("BOT", self.coupling.mf6_model, "DIS")
        mf6_max_iter_tag = self.mf6.get_var_address("MXITER", "SLN_1")

        self.mf6_head = self.mf6.get_value_ptr(mf6_head_tag)
        # NB: recharge is set to first column in BOUND
        self.mf6_recharge = self.mf6.get_value_ptr(mf6_recharge_tag)[:, 0]
        self.mf6_storage = self.mf6.get_value_ptr(mf6_storage_tag)
        self.mf6_has_sc1 = self.mf6.get_value_ptr(mf6_is_sc1_tag)[0] != 0
        self.mf6_area = self.mf6.get_value_ptr(mf6_area_tag)
        self.mf6_top = self.mf6.get_value_ptr(mf6_top_tag)
        self.mf6_bot = self.mf6.get_value_ptr(mf6_bot_tag)
        self.max_iter = self.mf6.get_value_ptr(mf6_max_iter_tag)[0]

        self.msw_head = self.msw.get_value_ptr("dhgwmod")
        self.msw_volume = self.msw.get_value_ptr("dvsim")
        self.msw_storage = self.msw.get_value_ptr("dsc1sim")

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

        # create mappings
        table_node2svat: NDArray[np.int32] = np.loadtxt(
            self.coupling.mf6_msw_node_map, dtype=np.int32, ndmin=2
        )
        node_idx = table_node2svat[:, 0] - 1
        msw_idx = [
            svat_lookup[table_node2svat[ii, 1], table_node2svat[ii, 2]]
            for ii in range(len(table_node2svat))
        ]

        self.map_msw2mod["storage"], self.mask_msw2mod["storage"] = create_mapping(
            msw_idx,
            node_idx,
            self.msw_storage.size,
            self.mf6_storage.size,
            "sum",
        )

        # MetaSWAP gives SC1*area, MODFLOW by default needs SS, convert here.
        # When MODFLOW is configured to use SC1 explicitly via the
        # STORAGECOEFFICIENT option in the STO package, only the multiplication
        # by area needs to be undone
        if self.mf6_has_sc1:
            conversion_terms = 1.0 / self.mf6_area
        else:
            conversion_terms = 1.0 / self.mf6_area * (self.mf6_top - self.mf6_bot)

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
        msw_idx = [
            svat_lookup[table_rch2svat[ii, 1], table_rch2svat[ii, 2]]
            for ii in range(len(table_rch2svat))
        ]

        self.map_msw2mod["recharge"], self.mask_msw2mod["recharge"] = create_mapping(
            msw_idx,
            rch_idx,
            self.msw_volume.size,
            self.mf6_recharge.size,
            "sum",
        )

        if self.coupling.enable_sprinkling:
            assert isinstance(self.coupling.mf6_msw_well_pkg, str)
            assert isinstance(self.coupling.mf6_msw_sprinkling_map, Path)

            # in this case we have a sprinkling demand from MetaSWAP
            mf6_sprinkling_tag = self.mf6.get_var_address(
                "BOUND", self.coupling.mf6_model, self.coupling.mf6_msw_well_pkg
            )
            self.mf6_sprinkling_wells = self.mf6.get_value_ptr(mf6_sprinkling_tag)[:, 0]
            table_well2svat: NDArray[np.int32] = np.loadtxt(
                self.coupling.mf6_msw_sprinkling_map, dtype=np.int32, ndmin=2
            )
            well_idx = table_well2svat[:, 0] - 1
            msw_idx = [
                svat_lookup[table_well2svat[ii, 1], table_well2svat[ii, 2]]
                for ii in range(len(table_well2svat))
            ]

            (
                self.map_msw2mod["sprinkling"],
                self.mask_msw2mod["sprinkling"],
            ) = create_mapping(
                msw_idx,
                well_idx,
                self.msw_volume.size,
                self.mf6_sprinkling_wells.size,
                "sum",
            )

    def update(self) -> None:
        # heads to MetaSWAP
        self.exchange_mod2msw()

        # we cannot set the timestep (yet) in Modflow
        # -> set to the (dummy) value 0.0 for now
        self.mf6.prepare_time_step(0.0)

        self.delt = self.mf6.get_time_step()
        self.msw.prepare_time_step(self.delt)

        # convergence loop
        self.mf6.prepare_solve(1)
        for kiter in range(1, self.max_iter + 1):
            has_converged = self.do_iter(1)
            if has_converged:
                logger.debug(f"MF6-MSW converged in {kiter} iterations")
                break
        self.mf6.finalize_solve(1)

        self.mf6.finalize_time_step()
        self.msw_time = self.mf6.get_current_time()
        self.msw.finalize_time_step()

    def finalize(self) -> None:
        self.mf6.finalize()
        self.msw.finalize()

    def get_current_time(self) -> float:
        return self.mf6.get_current_time()

    def get_end_time(self) -> float:
        return self.mf6.get_end_time()

    def exchange_msw2mod(self) -> None:
        """Exchange Metaswap to Modflow"""
        self.mf6_storage[:] = (
            self.mask_msw2mod["storage"][:] * self.mf6_storage[:]
            + self.map_msw2mod["storage"].dot(self.msw_storage)[:]
        )

        # Divide recharge and extraction by delta time
        tled = 1 / self.delt
        self.mf6_recharge[:] = (
            self.mask_msw2mod["recharge"][:] * self.mf6_recharge[:]
            + tled * self.map_msw2mod["recharge"].dot(self.msw_volume)[:]
        )

        if self.coupling.enable_sprinkling:
            self.mf6_sprinkling_wells[:] = (
                self.mask_msw2mod["sprinkling"][:] * self.mf6_sprinkling_wells[:]
                + tled * self.map_msw2mod["sprinkling"].dot(self.msw_volume)[:]
            )

    def exchange_mod2msw(self) -> None:
        """Exchange Modflow to Metaswap"""
        self.msw_head[:] = (
            self.mask_mod2msw["head"][:] * self.msw_head[:]
            + self.map_mod2msw["head"].dot(self.mf6_head)[:]
        )

    def do_iter(self, sol_id: int) -> bool:
        """Execute a single iteration"""
        self.msw.prepare_solve(0)
        self.msw.solve(0)
        self.exchange_msw2mod()
        has_converged = self.mf6.solve(sol_id)
        self.exchange_mod2msw()
        self.msw.finalize_solve(0)
        return has_converged

    def report_timing_totals(self) -> None:
        total_mf6 = self.mf6.report_timing_totals()
        total_msw = self.msw.report_timing_totals()
        total = total_mf6 + total_msw
        logger.info(f"Total elapsed time in numerical kernels: {total:0.4f} seconds")
