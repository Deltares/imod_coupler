import logging
import os

import numpy as np

from xmipy import XmiWrapper
from imod_coupler.utils import create_mapping

logger = logging.getLogger(__name__)


class MetaMod:
    def __init__(self, mf6: XmiWrapper, msw: XmiWrapper, timing: bool = False):
        """Defines the class usable to couple Metaswap and Modflow"""
        self.timing = timing
        self.mf6 = mf6
        self.msw = msw

        # define (and document!) instance attributes here:
        self.max_iter = None  # max. nr outer iterations in MODFLOW kernel
        self.delt = None  # time step from MODFLOW 6 (leading)

        self.mf6_head = None  # the hydraulic head array in the coupled model
        self.mf6_recharge = None  # the coupled recharge array from the RCH package
        self.mf6_storage = None  # the storage coefficients array (sc1)
        self.mf6_sprinkling_wells = None  # the well data for coupled extractions
        self.is_sprinkling_active = None  # true when sprinkling is active

        self.msw_head = None  # internal MetaSWAP groundwater head
        self.msw_volume = None  # unsaturated zone flux (as a volume!)
        self.msw_storage = None  # MetaSWAP storage coefficients (MODFLOW's sc1)
        self.msw_time = None  # MetaSWAP current time

        self.map_mod2msw = None  # dictionary with mapping tables for mod=>msw coupling
        self.map_msw2mod = None  # dictionary with mapping tables for msw=>mod coupling
        self.mask_mod2msw = None  # dict. with mask arrays for mod=>msw coupling
        self.mask_msw2mod = None  # dict. with mask arrays for msw=>mod coupling

        self.couple()

    def get_mf6_modelname(self):
        """Extract the model name from the the mf6_config_file."""
        mfsim_name = os.path.join(self.mf6.working_directory, "mfsim.nam")
        with open(mfsim_name, "r") as mfsim:
            for ndx, line in enumerate(mfsim):
                if "BEGIN MODELS" in line.upper():
                    break
            modeltype, modelnamfile, modelname = mfsim.readline().split()
            return modelname.upper()

    def xchg_msw2mod(self):
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

    def xchg_mod2msw(self):
        """Exchange Modflow to Metaswap"""
        self.msw_head[:] = (
            self.mask_mod2msw["head"][:] * self.msw_head[:]
            + self.map_mod2msw["head"].dot(self.mf6_head)[:]
        )

    def do_iter(self, sol_id: int) -> bool:
        """Execute a single iteration"""
        self.msw.prepare_solve(0)
        self.msw.solve(0)
        self.xchg_msw2mod()
        has_converged = self.mf6.solve(sol_id)
        self.xchg_mod2msw()
        self.msw.finalize_solve(0)
        return has_converged

    def update_coupled(self):
        """Advance by one timestep"""

        # heads to MetaSWAP
        self.xchg_mod2msw()

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

    def get_times(self):
        """Return times"""
        return (
            self.mf6.get_start_time(),
            self.mf6.get_current_time(),
            self.mf6.get_end_time(),
        )

    def couple(self):
        """Couple Modflow and Metaswap"""
        # get some 'pointers' to MF6 and MSW internal data
        mf6_modelname = self.get_mf6_modelname()
        mf6_head_tag = self.mf6.get_var_address("X", mf6_modelname)
        mf6_recharge_tag = self.mf6.get_var_address("BOUND", mf6_modelname, "RCH_MSW")
        mf6_storage_tag = self.mf6.get_var_address("SC1", mf6_modelname, "STO")
        mf6_sprinkling_tag = self.mf6.get_var_address(
            "BOUND", mf6_modelname, "WELLS_MSW"
        )
        mf6_max_iter_tag = self.mf6.get_var_address("MXITER", "SLN_1")

        self.mf6_head = self.mf6.get_value_ptr(mf6_head_tag)
        # NB: recharge is set to first column in BOUND
        self.mf6_recharge = self.mf6.get_value_ptr(mf6_recharge_tag)[:, 0]
        self.mf6_storage = self.mf6.get_value_ptr(mf6_storage_tag)
        self.max_iter = self.mf6.get_value_ptr(mf6_max_iter_tag)[0]

        # check if we have sprinkling
        self.is_sprinkling_active = False
        if mf6_sprinkling_tag in self.mf6.get_output_var_names():
            self.mf6_sprinkling_wells = self.mf6.get_value_ptr(mf6_sprinkling_tag)[:, 0]
            self.is_sprinkling_active = True

        self.msw_head = self.msw.get_value_ptr("dhgwmod")
        self.msw_volume = self.msw.get_value_ptr("dvsim")
        self.msw_storage = self.msw.get_value_ptr("dsc1sim")
        self.msw_time = self.msw.get_value_ptr("currenttime")

        # mappings and masks for each set of coupled variables between
        # msw and mod, see (the documentation of) the create_mapping
        # function for further details
        map_mod2msw = {}
        map_msw2mod = {}
        mask_mod2msw = {}
        mask_msw2mod = {}

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

            map_msw2mod["storage"], mask_msw2mod["storage"] = create_mapping(
                msw_idx,
                node_idx,
                self.msw_storage.size,
                self.mf6_storage.size,
                "sum",
            )

            map_mod2msw["head"], mask_mod2msw["head"] = create_mapping(
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

            map_msw2mod["recharge"], mask_msw2mod["recharge"] = create_mapping(
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

                map_msw2mod["sprinkling"], mask_msw2mod["sprinkling"] = create_mapping(
                    msw_idx,
                    well_idx,
                    self.msw_volume.size,
                    self.mf6_sprinkling_wells.size,
                    "sum",
                )
            else:
                raise Exception("Can't find " + mapping_file_recharge)

        self.map_mod2msw = map_mod2msw
        self.map_msw2mod = map_msw2mod
        self.mask_mod2msw = mask_mod2msw
        self.mask_msw2mod = mask_msw2mod
