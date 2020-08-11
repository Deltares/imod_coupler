import logging
import os

import numpy as np

from xmipy import XmiWrapper
from imod_coupler.utils import read_mapping, invert_mapping

logger = logging.getLogger(__name__)


class MetaMod:
    def __init__(
        self,
        config_data,
        timing: bool = False
    ):
        """Defines the class usable to couple Metaswap and Modflow"""
        self.timing = timing
        deps = config_data['dependencies']
        for dep in deps:
            if not os.path.isdir(dep):
                raise Exception(f"Dependend directory {dep} not found.")
        for label, cmp in config_data['components'].items():
            if not os.path.exists(cmp['dll']):
                raise Exception(f"Component {label} dll {cmp['dll']} not found.")
            if not os.path.isdir(cmp['wd']):
                raise Exception(
                    f"Component {label} working directory {cmp['wd']} not found.")
            new_xmi = XmiWrapper(cmp['dll'], deps,
                                 working_directory=cmp['wd'],
                                 timing=self.timing)
            if label == 'mf6':
                new_xmi.set_int("ISTDOUTTOFILE", 0)
                new_xmi.initialize()
                self.mf6 = new_xmi
            if label == 'msw':
                new_xmi.initialize()
                self.msw = new_xmi

        self.couple(config_data)

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
        for i in range(self.ncell_mod):
            if i in self.map_mod2msw["storage"]:
                self.mf6_storage[i] = np.sum(
                    self.msw_storage[self.map_mod2msw["storage"][i]]
                )
        for i in range(self.ncell_recharge):
            if i in self.map_mod2msw["recharge"]:
                # Divide by delta time,
                # since Metaswap only keeps track of volumes
                # leaving its domain, not fluxes
                # Multiply with -1 as recharge is leaving MetaSWAP (negative)
                # and entering MF6 (positive)
                self.mf6_recharge[i] = (
                    -1
                    * np.sum(self.msw_volume[self.map_mod2msw["recharge"][i]])
                    / self.delt
                )

    def xchg_mod2msw(self):
        """Exchange Modflow to Metaswap"""
        for i in range(self.ncell_msw):
            if i in self.map_msw2mod["head"]:
                self.msw_head[i] = np.mean(self.mf6_head[self.map_msw2mod["head"][i]])

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

    def report_timing_totals(self):
        """Report total time spent in numerical kernels to logger"""
        if self.timing:
            total = self.mf6.report_timing_totals() + self.msw.report_timing_totals()
            logger.info(
                f"Total elapsed time in numerical kernels: {total:0.4f} seconds"
            )
            return total
        else:
            raise Exception("Timing not activated")

    def couple(self, config_data):
        """Couple Modflow and Metaswap"""
        # get some 'pointers' to MF6 and MSW internal data
        mf6_modelname = self.get_mf6_modelname()
        self.mf6_head = self.mf6.get_value_ptr("SLN_1/X")
        self.mf6_recharge = self.mf6.get_value_ptr(f"{mf6_modelname} RCH-1/BOUND")
        self.mf6_storage = self.mf6.get_value_ptr(f"{mf6_modelname} STO/SC2")
        self.ncell_mod = np.size(self.mf6_storage)
        self.ncell_recharge = np.size(self.mf6_recharge)
        self.max_iter = self.mf6.get_value_ptr("SLN_1/MXITER")[0]
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
            map_mod2msw["storage"] = read_mapping(mapping_file)
        else:
            raise Exception("Missing mod2svat.inp")

        map_msw2mod["head"] = invert_mapping(map_mod2msw["storage"])
        self.map_msw2mod = map_msw2mod
        self.map_mod2msw = map_mod2msw

        mapping_file_recharge = os.path.join(
            self.msw.working_directory, "mod2svat_recharge.inp"
        )
        if os.path.isfile(mapping_file_recharge):
            map_mod2msw["recharge"] = read_mapping(mapping_file_recharge)
        else:
            raise Exception("Missing mod2svat_recharge.inp")

        self.map_mod2msw = map_mod2msw
        self.map_msw2map = map_msw2mod
        self.xchg_mod2msw()
