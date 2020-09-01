import logging
import os

import numpy as np

from xmipy import XmiWrapper
from imod_coupler.utils import read_mapping

logger = logging.getLogger(__name__)


class MetaMod:
    def __init__(self, mf6: XmiWrapper, msw: XmiWrapper, timing: bool = False):
        """Defines the class usable to couple Metaswap and Modflow"""
        self.timing = timing
        self.mf6 = mf6
        self.msw = msw

        self.couple()

    def get_mf6_modelname(self):
        """Extract the model name from the the mf6_config_file."""
        mfsim_name = os.path.join(self.mf6.working_directory, "mfsim.nam")
        with open(mfsim_name, "r") as mfsim:
            for ndx, line in enumerate(mfsim):
                if "BEGIN MODELS" in line:
                    break
            modeltype, modelnamfile, modelname = mfsim.readline().split()
            return modelname.upper()

    def xchg_msw2mod(self):
        """Exchange Metaswap to Modflow"""
        self.mf6_storage[:] = self.map_mod2msw["storage"].dot(self.msw_storage)[:]
        self.mf6_sto_reset[0] = 1
        # Divide by delta time,
        # since Metaswap only keeps track of volumes
        # leaving its domain, not fluxes
        # Multiply with -1 as recharge is leaving MetaSWAP (negative)
        # and entering MF6 (positive)

        self.mf6_recharge[:] = self.map_mod2msw["recharge"].dot(self.msw_volume)[:]
        self.mf6_recharge[:] /= -1.0 * self.delt

    def xchg_mod2msw(self):
        """Exchange Modflow to Metaswap"""
        self.msw_head[:] = self.map_msw2mod["head"].dot(self.mf6_head)[:]

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

        # loop over subcomponents
        n_solutions = self.mf6.get_subcomponent_count()
        for sol_id in range(1, n_solutions + 1):
            # convergence loop
            self.mf6.prepare_solve(sol_id)
            for kiter in range(self.max_iter):
                has_converged = self.do_iter(sol_id)
                if has_converged:
                    logger.debug(f"Component {sol_id} converged in {kiter} iterations")
                    break
            self.mf6.finalize_solve(sol_id)

        self.mf6.finalize_time_step()
        current_time = self.mf6.get_current_time()
        self.msw_time = current_time
        self.msw.finalize_time_step()
        return current_time

    def getTimes(self):
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
        mf6_head_tag = self.mf6.get_var_address("X", "SLN_1")
        mf6_recharge_tag = self.mf6.get_var_address("BOUND", mf6_modelname, "RCH-1")
        mf6_storage_tag = self.mf6.get_var_address("SC1", mf6_modelname, "STO")
        mf6_sto_reset_tag = self.mf6.get_var_address("IRESETSC1", mf6_modelname, "STO")
        mf6_max_iter_tag = self.mf6.get_var_address("MXITER", "SLN_1")

        self.mf6_head = self.mf6.get_value_ptr(mf6_head_tag)
        # NB: recharge is set to first column in BOUND
        self.mf6_recharge = self.mf6.get_value_ptr(mf6_recharge_tag)[:, 0]
        self.mf6_storage = self.mf6.get_value_ptr(mf6_storage_tag)
        self.mf6_sto_reset = self.mf6.get_value_ptr(mf6_sto_reset_tag)
        self.max_iter = self.mf6.get_value_ptr(mf6_max_iter_tag)[0]

        self.ncell_mod = np.size(self.mf6_storage)
        self.ncell_recharge = np.size(self.mf6_recharge)

        self.msw_head = self.msw.get_value_ptr("dhgwmod")
        self.msw_volume = self.msw.get_value_ptr("dvsim")
        self.msw_storage = self.msw.get_value_ptr("dsc1sim")
        self.msw_time = self.msw.get_value_ptr("currenttime")

        self.ncell_msw = np.size(self.msw_storage)

        # map_msw2mod is a dict (size nid) of lists so that xchg[i]
        # holds the list of swat indices associated with the i-th gw-cell
        #       or a list of scalar indices
        # The mapping between gw cells and svats can be n-to-m

        map_mod2msw = {}
        map_msw2mod = {}

        mapping_file = os.path.join(self.msw.working_directory, "mod2svat.inp")
        if os.path.isfile(mapping_file):
            map_mod2msw["storage"] = read_mapping(
                mapping_file, self.mf6_storage.size, self.msw_storage.size, "sum", False
            )
            map_msw2mod["head"] = read_mapping(
                mapping_file, self.msw_head.size, self.mf6_head.size, "avg", True
            )
        else:
            raise Exception("Missing mod2svat.inp")

        mapping_file_recharge = os.path.join(
            self.msw.working_directory, "mod2svat_recharge.inp"
        )
        if os.path.isfile(mapping_file_recharge):
            map_mod2msw["recharge"] = read_mapping(
                mapping_file_recharge,
                self.msw_volume.size,
                self.mf6_recharge.size,
                "sum",
                False,
            )
        else:
            raise Exception("Missing mod2svat_recharge.inp")

        self.map_mod2msw = map_mod2msw
        self.map_msw2mod = map_msw2mod
