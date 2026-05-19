"""MetaMod: the coupling between MetaSWAP and MODFLOW 6

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
from imod_coupler.drivers.metamod.config import Coupling, MetaModConfig
from imod_coupler.kernelwrappers.mf6_newton_wrapper import (
    PhreaticHeads,
    PhreaticRecharge,
    PhreaticStorage,
)
from imod_coupler.kernelwrappers.mf6_wrapper import Mf6Wrapper
from imod_coupler.kernelwrappers.msw_wrapper import MswWrapper
from imod_coupler.logging.exchange_collector import ExchangeCollector
from imod_coupler.utils import create_mapping


class MetaMod(Driver):
    """The driver coupling MetaSWAP and MODFLOW 6"""

    base_config: BaseConfig  # the parsed information from the configuration file
    metamod_config: MetaModConfig  # the parsed information from the configuration file specific to MetaMod
    coupling: Coupling  # the coupling information

    timing: bool  # true, when timing is enabled
    mf6: Mf6Wrapper  # the MODFLOW 6 XMI kernel
    msw: MswWrapper  # the MetaSWAP XMI kernel

    max_iter: NDArray[Any]  # max. nr outer iterations in MODFLOW kernel
    delt: float  # time step from MODFLOW 6 (leading)

    mf6_head: NDArray[Any]  # the hydraulic head array in the coupled model
    mf6_recharge: NDArray[np.float64]  # the coupled recharge array from the RCH package
    mf6_ss: NDArray[Any]  # the specific storage array (ss)
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

    svat_lookup: dict[str, NDArray[Any]] = {}

    node_idx: NDArray[Any]  # mf6 nodes coupled to msw
    msw_idx: NDArray[Any]  # msw nodes coupled to MF6

    def __init__(self, base_config: BaseConfig, metamod_config: MetaModConfig):
        """Constructs the `MetaMod` object"""
        self.base_config = base_config
        self.metamod_config = metamod_config
        self.coupling = metamod_config.coupling[
            0
        ]  # Adapt as soon as we have multimodel support
        self.enable_sprinkling_groundwater = False

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
        if self.coupling.output_config_file is not None:
            self.exchange_logger = ExchangeCollector.from_file(
                self.coupling.output_config_file
            )
        else:
            self.exchange_logger = ExchangeCollector()
        self.couple()

    def log_version(self) -> None:
        logger.info(f"MODFLOW version: {self.mf6.get_version()}")
        logger.info(f"MetaSWAP version: {self.msw.get_version()}")

    def couple(self) -> None:
        """Couple Modflow and Metaswap"""

        self.mf6_head = self.mf6.get_head(self.coupling.mf6_model)
        self.mf6_recharge = self.mf6.get_recharge(
            self.coupling.mf6_model, self.coupling.mf6_msw_recharge_pkg
        )
        self.mf6_ss = self.mf6.get_ss(self.coupling.mf6_model)
        self.mf6_has_sc1 = self.mf6.has_sc1(self.coupling.mf6_model)
        self.mf6_area = self.mf6.get_area(self.coupling.mf6_model)
        self.mf6_top = self.mf6.get_top(self.coupling.mf6_model)
        self.mf6_bot = self.mf6.get_bot(self.coupling.mf6_model)
        self.max_iter = self.mf6.max_iter()

        self.msw_head = self.msw.get_head_ptr()
        self.msw_volume = self.msw.get_volume_ptr()
        self.msw_storage = self.msw.get_storage_ptr()

        # create a lookup, with the svat tuples (id, lay) as keys and the
        # metaswap internal indexes as values
        msw_mod2svat_file = self.msw.working_directory / "mod2svat.inp"
        if msw_mod2svat_file.is_file():
            svat_data: NDArray[np.int32] = np.loadtxt(
                msw_mod2svat_file, dtype=np.int32, ndmin=2
            )
            svat_id = svat_data[:, 1]
            svat_lay = svat_data[:, 2]
            for vi in range(svat_id.size):
                self.svat_lookup[(svat_id[vi], svat_lay[vi])] = vi
        else:
            raise ValueError(f"Can't find {msw_mod2svat_file}.")

        # create mappings
        table_node2svat: NDArray[np.int32] = np.loadtxt(
            self.coupling.mf6_msw_node_map, dtype=np.int32, ndmin=2
        )
        self.node_idx = table_node2svat[:, 0] - 1
        self.msw_idx = np.array(
            [
                self.svat_lookup[table_node2svat[ii, 1], table_node2svat[ii, 2]]
                for ii in range(len(table_node2svat))
            ]
        )
        self.map_msw2mod["storage"], self.mask_msw2mod["storage"] = create_mapping(
            self.msw_idx,
            self.node_idx,
            self.msw_storage.size,
            self.mf6_ss.size,
            "sum",
        )

        # MetaSWAP gives SC1*area, MODFLOW by default needs SS, convert here.
        # When MODFLOW is configured to use SC1 explicitly via the
        # STORAGECOEFFICIENT option in the STO package, only the multiplication
        # by area needs to be undone
        if self.mf6_has_sc1:
            conversion_terms = 1.0 / self.mf6_area
        else:
            conversion_terms = 1.0 / (self.mf6_area * (self.mf6_top - self.mf6_bot))

        conversion_matrix = dia_matrix(
            (conversion_terms, [0]),
            shape=(self.mf6_area.size, self.mf6_area.size),
            dtype=self.mf6_area.dtype,
        )
        self.map_msw2mod["storage"] = conversion_matrix * self.map_msw2mod["storage"]

        self.map_mod2msw["head"], self.mask_mod2msw["head"] = create_mapping(
            self.node_idx,
            self.msw_idx,
            self.mf6_head.size,
            self.msw_head.size,
            "avg",
        )

        table_rch2svat: NDArray[np.int32] = np.loadtxt(
            self.coupling.mf6_msw_recharge_map, dtype=np.int32, ndmin=2
        )
        rch_idx = table_rch2svat[:, 0] - 1
        self.msw_idx = np.array(
            [
                self.svat_lookup[table_rch2svat[ii, 1], table_rch2svat[ii, 2]]
                for ii in range(len(table_rch2svat))
            ]
        )

        self.map_msw2mod["recharge"], self.mask_msw2mod["recharge"] = create_mapping(
            self.msw_idx,
            rch_idx,
            self.msw_volume.size,
            self.mf6_recharge.size,
            "sum",
        )

        if self.coupling.mf6_msw_sprinkling_map_groundwater is not None:
            assert isinstance(self.coupling.mf6_msw_well_pkg, str)
            assert isinstance(self.coupling.mf6_msw_sprinkling_map_groundwater, Path)

            # in this case we have a sprinkling demand from MetaSWAP
            self.mf6_sprinkling_wells = self.mf6.get_well(
                self.coupling.mf6_model, self.coupling.mf6_msw_well_pkg
            )
            table_well2svat: NDArray[np.int32] = np.loadtxt(
                self.coupling.mf6_msw_sprinkling_map_groundwater,
                dtype=np.int32,
                ndmin=2,
            )
            well_idx = table_well2svat[:, 0] - 1
            self.msw_idx = np.array(
                [
                    self.svat_lookup[table_well2svat[ii, 1], table_well2svat[ii, 2]]
                    for ii in range(len(table_well2svat))
                ]
            )

            (
                self.map_msw2mod["sprinkling"],
                self.mask_msw2mod["sprinkling"],
            ) = create_mapping(
                self.msw_idx,
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
        self.msw.finalize_time_step()

        if not has_converged:
            logger.debug("MF6-MSW did not converge")
            # raise ValueError("MF6-MSW did not converge")

    def finalize(self) -> None:
        self.mf6.finalize()
        self.msw.finalize()
        self.exchange_logger.finalize()

    def get_current_time(self) -> float:
        return self.mf6.get_current_time()

    def get_end_time(self) -> float:
        return self.mf6.get_end_time()

    def exchange_msw2mod(self) -> None:
        """Exchange Metaswap to Modflow"""
        self.mf6_ss[:] = (
            self.mask_msw2mod["storage"][:] * self.mf6_ss[:]
            + self.map_msw2mod["storage"].dot(self.msw_storage)[:]
        )
        self.exchange_logger.log_exchange(
            "mf6_storage", self.mf6_ss, self.get_current_time()
        )
        self.exchange_logger.log_exchange(
            "msw_storage", self.msw_storage, self.get_current_time()
        )

        # Set recharge
        nodelist_address = self.mf6.get_var_address(
            "NODELIST", self.coupling.mf6_model, self.coupling.mf6_msw_recharge_pkg
        )
        nodelist = self.mf6.get_value_ptr(nodelist_address)
        self.mf6_recharge[:] = (
            self.mask_msw2mod["recharge"][:] * self.mf6_recharge[:]
            + self.map_msw2mod["recharge"].dot(self.msw_volume)[:] / self.delt
        ) / self.mf6_area[nodelist]

        if self.enable_sprinkling_groundwater:
            self.mf6_sprinkling_wells[:] = (
                self.mask_msw2mod["sprinkling"][:] * self.mf6_sprinkling_wells[:]
                + self.map_msw2mod["sprinkling"].dot(self.msw_volume)[:] / self.delt
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


class MetaModNewton(MetaMod):
    """
    MetaModNewton: the coupling between MetaSWAP and MODFLOW 6, for the Newton formulation of MODFLOW 6
    """

    uzf_active: bool = True

    def __init__(self, base_config: BaseConfig, metamod_config: MetaModConfig):
        super().__init__(base_config, metamod_config)

    def couple(self) -> None:
        super().couple()
        # Mapping for heads, SY and SS based on the top layer subset of MODFLOW 6 model arrays.
        # The PhreaticHeads + PhreaticStorage methods get and set values to the corresponding
        # phreatic nodes of potential deeper layers.
        first_layer_nodes = self.get_first_layer_nodes()
        self.map_mod2msw["head"], self.mask_mod2msw["head"] = create_mapping(
            self.node_idx,
            self.msw_idx,
            first_layer_nodes.size,
            self.msw_head.size,
            "avg",
        )
        # mapping for SS now to top layer subset
        self.map_msw2mod["storage"], self.mask_msw2mod["storage"] = create_mapping(
            self.msw_idx,
            self.node_idx,
            self.msw_storage.size,
            first_layer_nodes.size,
            "sum",
        )
        conversion_matrix = self.sto_conversion_terms(
            self.mf6_has_sc1, first_layer_nodes
        )
        self.map_msw2mod["storage"] = conversion_matrix * self.map_msw2mod["storage"]
        # Create extra mapping for SY, since the SS mapping could contains a different conversion term
        (
            self.map_msw2mod["storage_sy"],
            self.mask_msw2mod["storage_sy"],
        ) = create_mapping(
            self.msw_idx,
            self.node_idx,
            self.msw_storage.size,
            first_layer_nodes.size,
            "sum",
        )
        # For exchange to SY, act as is sc1
        conversion_matrix = self.sto_conversion_terms(True, first_layer_nodes)
        self.map_msw2mod["storage_sy"] = (
            conversion_matrix * self.map_msw2mod["storage_sy"]
        )
        # get max layer per MF6-node
        self.max_layer_index = None
        if self.coupling.mf6_node_max_layer is not None:
            table_node_layer: NDArray[np.int32] = np.loadtxt(
                self.coupling.mf6_node_max_layer, dtype=np.int64, ndmin=2, skiprows=1
            )
            self.max_layer_index = table_node_layer[:, 1] - 1
        # Add Newton related phreatic exchange classes
        self.couple_phreatic(first_layer_nodes)
        # Add optional UZF-coupling
        self.couple_uzf(first_layer_nodes)

    def couple_uzf(
        self,
        first_layer_nodes: NDArray[np.int32],
    ) -> None:
        if self.coupling.mf6_uzf_pkg is None:
            self.uzf_active = False
            return
        self.mf6_uzf = self.mf6.get_uzf_infiltration(
            self.coupling.mf6_model, self.coupling.mf6_uzf_pkg
        )

        self.uzf_nodelist = (
            self.mf6.get_uzf_nodes(self.coupling.mf6_model, self.coupling.mf6_uzf_pkg)
            - 1
        )
        self.userid = self.mf6_get_userid() - 1
        nlay, nrow, ncol = self.mf6.get_dis_shape(self.coupling.mf6_model)

        # user nodes, flat
        mf6_index_2d = np.full((nlay * nrow * ncol), -1, dtype=np.int32)
        uzf_index_2d = np.full((nlay * nrow * ncol), -1, dtype=np.int32)
        # add mf6 reduced nodes to user nodes
        mf6_index_2d[self.userid[self.uzf_nodelist]] = self.uzf_nodelist
        uzf_index_2d[self.userid[self.uzf_nodelist]] = np.arange(self.uzf_nodelist.size)

        mf6_index_2d = mf6_index_2d.reshape((nlay, nrow * ncol))
        uzf_index_2d = uzf_index_2d.reshape((nlay, nrow * ncol))
        # find uzf index (model nodes) based on the giver max layer(model nodes)
        max_layer_index = self.max_layer_index + 1
        max_layer_index[max_layer_index > nlay - 1] = nlay - 1

        mf6_index = mf6_index_2d[max_layer_index, first_layer_nodes - 1]
        uzf_index = uzf_index_2d[max_layer_index, first_layer_nodes - 1]

        self.mf6_rch_index = np.arange(mf6_index.size, dtype=np.int32)[
            mf6_index > -1
        ]  # projection to 2D (x,y) plane of rch grid
        self.mf6_index = mf6_index[mf6_index > -1]
        self.uzf_index = uzf_index[uzf_index > -1]
        self.uzf_bottom = self.mf6.get_bot(self.coupling.mf6_model)[self.mf6_index]
        landflag = self.mf6.get_uzf_landflag(
            self.coupling.mf6_model, self.coupling.mf6_uzf_pkg
        )
        # be sure to set landflag so we can set infiltration properly
        landflag[self.uzf_index] = 1
        # get active uzf nodes relative to the 2d plane of the rch grid
        self.uzf_active_mask = np.full_like(first_layer_nodes, False, dtype=bool)
        self.uzf_active_mask[self.mf6_rch_index] = True
        self.uzf_mask = np.copy(self.uzf_active_mask)

    def couple_phreatic(self, first_layer_nodes: NDArray[Any]) -> None:
        userid = self.mf6_get_userid()
        saturation = self.mf6.get_saturation(self.coupling.mf6_model)
        self.sy = self.mf6.get_sy(self.coupling.mf6_model)
        self.sy_top = self.sy[first_layer_nodes]
        self.recharge_nodelist = self.mf6.get_recharge_nodes(
            self.coupling.mf6_model, self.coupling.mf6_msw_recharge_pkg
        )
        self.hds = PhreaticHeads(
            self.mf6.get_dis_shape(self.coupling.mf6_model),
            userid,
            saturation,
            self.mf6_head,
            first_layer_nodes,
            self.max_layer_index,
        )
        self.sto = PhreaticStorage(
            self.mf6.get_dis_shape(self.coupling.mf6_model),
            userid,
            saturation,
            self.sy,
            self.mf6_ss,
            first_layer_nodes,
            self.max_layer_index,
        )
        self.rch = PhreaticRecharge(
            self.mf6.get_dis_shape(self.coupling.mf6_model),
            userid,
            saturation,
            self.mf6_recharge,
            self.recharge_nodelist,
            self.max_layer_index,
        )

    def exchange_msw2uzf(self) -> None:
        # this method should be called per timestep, not per iteration, because
        # we can only update UZF infiltration values per timestep
        if not self.uzf_active:
            self.uzf_mask = np.full_like(self.mf6_head, False, dtype=bool)
            return
        new_recharge = (
            self.mask_msw2mod["recharge"][:] * self.mf6_recharge[:]
            + self.map_msw2mod["recharge"].dot(self.msw_volume)[:] / self.delt
        ) / self.mf6_area[self.recharge_nodelist - 1]
        self.mf6_uzf[self.uzf_index] = 0.0
        self.uzf_mask[:] = self.uzf_active_mask[:]
        self.uzf_mask[self.mf6_rch_index] = (
            self.mf6_head[self.mf6_rch_index] < self.uzf_bottom
        )
        self.mf6_uzf[self.uzf_index] = (
            new_recharge[self.mf6_rch_index] * self.uzf_mask[self.mf6_rch_index]
        )[:]

    def exchange_msw2mod(self) -> None:
        """Exchange Metaswap to Modflow"""
        new_sy = (
            self.mask_msw2mod["storage_sy"][:] * self.sy_top[:]
            + self.map_msw2mod["storage_sy"].dot(self.msw_storage)[:]
        )
        self.sto.reset()
        self.sto.set(new_sy)
        self.exchange_logger.log_exchange("mf6_sy", new_sy, self.get_current_time())
        self.exchange_logger.log_exchange(
            "msw_storage", self.msw_storage, self.get_current_time()
        )
        # Set recharge values

        # use mask to exchange with optional UZF-package for cases heads < msw_bot
        new_recharge = (
            self.mask_msw2mod["recharge"][:] * self.mf6_recharge[:]
            + self.map_msw2mod["recharge"].dot(self.msw_volume)[:] / self.delt
        ) / self.mf6_area[self.recharge_nodelist - 1]

        # Exchange only for elements that are not exchanged to UZF
        self.exchange_msw2uzf()
        self.rch.set(new_recharge * (self.uzf_mask == False))

        if self.enable_sprinkling_groundwater:
            self.mf6_sprinkling_wells[:] = (
                self.mask_msw2mod["sprinkling"][:] * self.mf6_sprinkling_wells[:]
                + self.map_msw2mod["sprinkling"].dot(self.msw_volume)[:] / self.delt
            )

    def exchange_mod2msw(self) -> None:
        """Exchange Modflow to Metaswap"""
        self.mf6_head = self.hds.get()
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
        # update nodelist rch-package
        self.rch.set_nodes()
        return has_converged

    def get_first_layer_nodes(self) -> NDArray[Any]:
        _, nrow, ncol = self.mf6.get_dis_shape(self.coupling.mf6_model)
        userid = self.mf6_get_userid()
        first_layer_ids = userid[userid <= (nrow * ncol)]
        if self.node_idx.max() > first_layer_ids.max():
            raise ValueError(
                "MetaSWAP could only be coupled to the first model layer of MODFLOW 6"
            )
        return first_layer_ids

    def get_bottom_coupled_nodes(self, layers, node_indx) -> NDArray[Any]:
        nlay, nrow, ncol = self.mf6.get_dis_shape(self.coupling.mf6_model)
        userid = self.mf6_get_userid()
        bottom_nodes = np.full(nlay * nrow * ncol, np.nan, dtype=np.float64)
        bottom_nodes[userid - 1] = self.mf6.get_bot(self.coupling.mf6_model)
        bottom_nodes = bottom_nodes.reshape((nlay, nrow * ncol))
        return bottom_nodes[layers - 1, userid[node_indx] - 1]

    def mf6_get_userid(self) -> NDArray[Any]:
        nlay, nrow, ncol = self.mf6.get_dis_shape(self.coupling.mf6_model)
        userid = self.mf6.get_nodeuser(self.coupling.mf6_model)
        if userid.size == 1:
            # no reduced domain, set userid to modelid
            # TODO: find out if there is a flag that indicates that usernodes == modelnodes
            userid = np.arange(nlay * nrow * ncol) + 1
        return userid

    def sto_conversion_terms(
        self, mf6_has_sc1: bool, indices: NDArray[Any]
    ) -> NDArray[Any]:
        if mf6_has_sc1:
            conversion_terms = 1.0 / self.mf6_area[indices]
        else:
            conversion_terms = 1.0 / (
                self.mf6_area[indices] * (self.mf6_top[indices] - self.mf6_bot[indices])
            )
        conversion_matrix = dia_matrix(
            (conversion_terms, [0]),
            shape=(self.mf6_area[indices].size, self.mf6_area[indices].size),
            dtype=self.mf6_area.dtype,
        )
        return conversion_matrix

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

        # per timestep

        for kiter in range(1, self.max_iter + 1):
            has_converged = self.do_iter(1)
            if has_converged:
                logger.debug(f"MF6-MSW converged in {kiter} iterations")
                break
        if not has_converged:
            raise ValueError("MF6-MSW did not converge")
        self.mf6.finalize_solve(1)
        self.msw.finalize_solve()  # ??

        self.mf6.finalize_time_step()
        self.msw.finalize_time_step()

        if not has_converged:
            logger.debug("MF6-MSW did not converge")
            # raise ValueError("MF6-MSW did not converge")
