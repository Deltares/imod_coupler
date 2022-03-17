""" MetaMod: the coupling between MetaSWAP and MODFLOW 6

description:

"""
import logging
import os
from pathlib import Path
from typing import Dict

import numpy as np
from scipy.sparse import dia_matrix
from xmipy import XmiWrapper

from imod_coupler.utils import create_mapping

logger = logging.getLogger(__name__)


class MetaMod:
    def __init__(self, config: Dict, config_path: Path):
        """Constructs the simulation object coupling MetaSWAP and MODFLOW 6"""

        # define (and document!) all instance attributes here:
        self.config_path = config_path
        self.config = config  # the parsed information from the configuration file

        self.timing = None  # true, when timing is enabled
        self.mf6 = None  # the MODFLOW 6 XMI kernel
        self.msw = None  # the MetaSWAP XMI kernel

        self.max_iter = None  # max. nr outer iterations in MODFLOW kernel
        self.delt = None  # time step from MODFLOW 6 (leading)

        self.mf6_head = None  # the hydraulic head array in the coupled model
        self.mf6_recharge = None  # the coupled recharge array from the RCH package
        self.mf6_storage = None  # the specific storage array (ss)
        self.mf6_area = None  # cell area (size:nodes)
        self.mf6_top = None  # top of cell (size:nodes)
        self.mf6_bot = None  # bottom of cell (size:nodes)

        self.is_sprinkling_active = None  # true when sprinkling is active
        self.mf6_model = None  # the MODFLOW 6 model that will be coupled
        self.mf6_msw_recharge_pkg = (
            None  # the recharge package that will be used for coupling
        )
        self.mf6_msw_well_pkg = None  # the well package that will be used for coupling when sprinkling is active
        self.mf6_msw_node_map = None  # the path to the node map file
        self.mf6_msw_recharge_map = None  # the pach to the recharge map file

        self.mf6_sprinkling_wells = None  # the well data for coupled extractions
        self.msw_head = None  # internal MetaSWAP groundwater head
        self.msw_volume = None  # unsaturated zone flux (as a volume!)
        self.msw_storage = None  # MetaSWAP storage coefficients (MODFLOW's sc1)
        self.msw_time = None  # MetaSWAP current time

        self.map_mod2msw = {}  # dictionary with mapping tables for mod=>msw coupling
        self.map_msw2mod = {}  # dictionary with mapping tables for msw=>mod coupling
        self.mask_mod2msw = {}  # dict. with mask arrays for mod=>msw coupling
        self.mask_msw2mod = {}  # dict. with mask arrays for msw=>mod coupling

    def initialize(self):
        """Initialize the coupled models"""
        # TODO: Set vars from config
        self.set_vars_from_config()

        # Print output to stdout
        self.mf6.set_int("ISTDOUTTOFILE", 0)
        self.mf6.initialize()
        self.msw.initialize()
        self.couple()

    def set_vars_from_config(self):
        self.mf6 = self.initialize_kernel_from_config("modflow6")
        self.msw = self.initialize_kernel_from_config("metaswap")

        # TODO: Relax this requirement as soon as we support multiple models
        assert len(self.config["driver"]["coupling"]) == 1
        coupling_config = self.config["driver"]["coupling"][0]

        self.is_sprinkling_active = coupling_config["enable_sprinkling"]
        self.mf6_model = coupling_config["mf6_model"]
        self.mf6_msw_recharge_pkg = coupling_config["mf6_msw_recharge_pkg"]
        self.mf6_msw_well_pkg = coupling_config["mf6_msw_well_pkg"]
        self.mf6_msw_node_map = coupling_config["mf6_msw_node_map"]
        self.mf6_msw_recharge_map = coupling_config["mf6_msw_recharge_map"]

    def get_absolute_path(self, path: str | Path) -> Path:
        path = Path(path)
        if path.is_absolute():
            return path
        else:
            return self.config_path.parent / path

    def initialize_kernel_from_config(self, kernel_name: str) -> XmiWrapper:
        # Validate paths
        dll_str = self.config["driver"]["kernels"][kernel_name]["dll"]
        dll = self.get_absolute_path(dll_str)
        if not dll.is_file():
            raise ValueError(
                f"'{dll}' for '{kernel_name}' is not a valid path to a file."
            )

        work_dir_str = self.config["driver"]["kernels"][kernel_name]["work_dir"]
        work_dir = self.get_absolute_path(work_dir_str)
        if not work_dir.is_dir():
            raise ValueError(
                f"'{work_dir}' for '{kernel_name}' is not a valid path to a directory."
            )

        if dll_dep_dir_str := self.config["driver"]["kernels"][kernel_name].get(
            "dll_dep_dir"
        ):
            dll_dep_dir = self.get_absolute_path(dll_dep_dir_str)
            if not dll_dep_dir.is_dir():
                raise ValueError(
                    f"'{dll_dep_dir}' for '{kernel_name}' is not a valid path to a directory."
                )
        else:
            dll_dep_dir = None

        return XmiWrapper(
            lib_path=dll,
            lib_dependency=dll_dep_dir,
            working_directory=work_dir,
            timing=self.config["timing"],
        )

    def couple(self):
        """Couple Modflow and Metaswap"""
        # get some 'pointers' to MF6 and MSW internal data
        mf6_head_tag = self.mf6.get_var_address("X", self.mf6_model)
        mf6_recharge_tag = self.mf6.get_var_address("BOUND", self.mf6_model, "RCH_MSW")
        mf6_storage_tag = self.mf6.get_var_address("SS", self.mf6_model, "STO")
        mf6_area_tag = self.mf6.get_var_address("AREA", self.mf6_model, "DIS")
        mf6_top_tag = self.mf6.get_var_address("TOP", self.mf6_model, "DIS")
        mf6_bot_tag = self.mf6.get_var_address("BOT", self.mf6_model, "DIS")
        mf6_sprinkling_tag = self.mf6.get_var_address(
            "BOUND", self.mf6_model, "WELLS_MSW"
        )
        mf6_max_iter_tag = self.mf6.get_var_address("MXITER", "SLN_1")

        self.mf6_head = self.mf6.get_value_ptr(mf6_head_tag)
        # NB: recharge is set to first column in BOUND
        self.mf6_recharge = self.mf6.get_value_ptr(mf6_recharge_tag)[:, 0]
        self.mf6_storage = self.mf6.get_value_ptr(mf6_storage_tag)
        self.mf6_area = self.mf6.get_value_ptr(mf6_area_tag)
        self.mf6_top = self.mf6.get_value_ptr(mf6_top_tag)
        self.mf6_bot = self.mf6.get_value_ptr(mf6_bot_tag)
        self.max_iter = self.mf6.get_value_ptr(mf6_max_iter_tag)[0]

        # check if we have sprinkling
        self.is_sprinkling_active = False
        if mf6_sprinkling_tag in self.mf6.get_output_var_names():
            self.mf6_sprinkling_wells = self.mf6.get_value_ptr(mf6_sprinkling_tag)[:, 0]
            self.is_sprinkling_active = True

        # print(f"{self.is_sprinkling_active=}")
        # breakpoint()
        self.msw_head = self.msw.get_value_ptr("dhgwmod")
        self.msw_volume = self.msw.get_value_ptr("dvsim")
        self.msw_storage = self.msw.get_value_ptr("dsc1sim")
        self.msw_time = self.msw.get_value_ptr("currenttime")

        # create a lookup, with the svat tuples (id, lay) as keys and the
        # metaswap internal indexes as values
        svat_lookup = {}
        msw_mod2svat_file = os.path.join(self.msw.working_directory, "mod2svat.inp")
        if os.path.isfile(msw_mod2svat_file):
            svat_data = np.loadtxt(msw_mod2svat_file, dtype=np.int32, ndmin=2)
            svat_id = svat_data[:, 1]
            svat_lay = svat_data[:, 2]
            for vi in range(svat_id.size):
                svat_lookup[(svat_id[vi], svat_lay[vi])] = vi
        else:
            raise Exception("Can't find " + msw_mod2svat_file)

        # create mappings
        mapping_file = os.path.join(self.mf6.working_directory, "nodenr2svat.dxc")
        if os.path.isfile(mapping_file):
            table_node2svat = np.loadtxt(mapping_file, dtype=np.int32, ndmin=2)
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

            # MetaSWAP gives SC1, MODFLOW needs SS, temporarily convert here,
            # following the definition on specific storage in chapter 5 of
            # the MODFLOW manual, but, this needs to be solved in MetaSWAP!!
            sc1_to_ss = 1.0 / np.multiply(self.mf6_area, self.mf6_top - self.mf6_bot)
            area_conversion = dia_matrix(
                (sc1_to_ss, [0]),
                shape=(self.mf6_area.size, self.mf6_area.size),
                dtype=self.mf6_area.dtype,
            )
            self.map_msw2mod["storage"] = area_conversion * self.map_msw2mod["storage"]

            self.map_mod2msw["head"], self.mask_mod2msw["head"] = create_mapping(
                node_idx,
                msw_idx,
                self.mf6_head.size,
                self.msw_head.size,
                "avg",
            )
        else:
            raise Exception("Can't find " + mapping_file)

        mapping_file_recharge = os.path.join(
            self.mf6.working_directory, "rchindex2svat.dxc"
        )
        if os.path.isfile(mapping_file_recharge):
            table_rch2svat = np.loadtxt(mapping_file_recharge, dtype=np.int32, ndmin=2)
            rch_idx = table_rch2svat[:, 0] - 1
            msw_idx = [
                svat_lookup[table_rch2svat[ii, 1], table_rch2svat[ii, 2]]
                for ii in range(len(table_rch2svat))
            ]

            (
                self.map_msw2mod["recharge"],
                self.mask_msw2mod["recharge"],
            ) = create_mapping(
                msw_idx,
                rch_idx,
                self.msw_volume.size,
                self.mf6_recharge.size,
                "sum",
            )
        else:
            raise Exception("Can't find " + mapping_file_recharge)

        if self.is_sprinkling_active:
            mapping_file_sprinkling = os.path.join(
                self.mf6.working_directory, "wellindex2svat.dxc"
            )
            if os.path.isfile(mapping_file_sprinkling):
                # in this case we have a sprinkling demand from MetaSWAP
                table_well2svat = np.loadtxt(
                    mapping_file_sprinkling, dtype=np.int32, ndmin=2
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
            else:
                raise Exception(f"Can't find {mapping_file_recharge}.")

    def update(self):
        """Perform a single time step"""
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
        current_time = self.mf6.get_current_time()
        self.msw_time = current_time
        self.msw.finalize_time_step()

        return current_time

    def finalize(self):
        """Cleanup the resources"""
        self.mf6.finalize()
        self.msw.finalize()

    def get_times(self):
        """Return times"""
        return (
            self.mf6.get_start_time(),
            self.mf6.get_current_time(),
            self.mf6.get_end_time(),
        )

    def exchange_msw2mod(self):
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

        if self.is_sprinkling_active:
            self.mf6_sprinkling_wells[:] = (
                self.mask_msw2mod["sprinkling"][:] * self.mf6_sprinkling_wells[:]
                + tled * self.map_msw2mod["sprinkling"].dot(self.msw_volume)[:]
            )

    def exchange_mod2msw(self):
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

    def report_timing_totals(self):
        total_mf6 = self.mf6.report_timing_totals()
        total_msw = self.msw.report_timing_totals()
        total = total_mf6 + total_msw
        logger.info(f"Total elapsed time in numerical kernels: {total:0.4f} seconds")
