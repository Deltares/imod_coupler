import json
import logging
import os
import sys

import numpy as np

from xmipy import XmiWrapper

logger = logging.getLogger(__name__)


def mapids(ids1, ids2):
    # Given id-list ids1 and ids2,
    # return a mapping coupling cells in ids1 to those in ids2
    # based on matching id ..... SAME as in mapids in driver_module
    dict = {}
    map_in = {}
    for i1 in range(len(ids1)):
        map_in[i1] = []
        id1 = ids1[i1]
        if id1 not in dict:
            dict[id1] = []
        dict[id1].append(i1)
    for i2 in range(len(ids1)):
        for i1 in dict[ids2[i2]]:  # for each id in ids1 equal to ids2[i2]
            map_in[i1].append(i2)  # add i2 to the list of connections
    return map_in


def read_mapping(map_file):

    map_arr = np.loadtxt(map_file, dtype=np.int32)
    map_arr[:, 0] = (
        map_arr[:, 0] - 1
    )  # 1-based indices (fortran) to 0-based indices (python)
    map_arr[:, 1] = map_arr[:, 1] - 1

    map_in = {}
    for gw, sv in zip(map_arr[:, 0], map_arr[:, 1]):
        map_in.setdefault(gw, []).append(sv)

    return map_in


def invert_mapping(map_in):
    map_out = {}
    for i, lst in map_in.items():
        for j in lst:
            if j not in map_out:
                map_out[j] = []
            map_out[j].append(i)
    for key in map_out.keys():
        map_out[key] = list(set(map_out[key]))
    return map_out


class MetaMod:
    def __init__(self, mf6_modeldir, msw_modeldir, mf6_dll, msw_dll, msw_dep, timing):
        self.timing = timing
        # Load and init Modflow 6
        self.mf6 = XmiWrapper(mf6_dll, timing=self.timing)
        self.mf6.working_directory = mf6_modeldir
        mf6_config_file = os.path.join(msw_modeldir, "mfsim.nam")
        self.mf6.set_int("ISTDOUTTOFILE", 0)
        self.mf6.initialize(mf6_config_file)

        # Load and init MetaSWAP
        self.msw = XmiWrapper(msw_dll, (msw_dep,), timing=self.timing)
        self.msw.working_directory = msw_modeldir
        self.msw.initialize(
            "config_file"
        )  # config file is a dummy argument, not used by msw

        self.couple()

    def get_mf6_modelname(self):
        # extract the model name from the the mf6_config_file
        mfsim_name = os.path.join(self.mf6.working_directory, "mfsim.nam")
        mfsim = open(mfsim_name, "r")
        mfsim_lines = mfsim.readlines()
        mfsim.close()
        for ndx, line in enumerate(mfsim_lines):
            if "BEGIN MODELS" in line:
                modeltype, modelnamfile, modelname = mfsim_lines[ndx + 1].split()
                return modelname

    def xchg_msw2mod(self):
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
        for i in range(self.ncell_msw):
            if i in self.map_msw2mod["head"]:
                self.msw_head[i] = np.mean(self.mf6_head[self.map_msw2mod["head"][i]])

    def do_iter(self, sol_id):
        self.msw.prepare_solve(0)
        self.msw.solve(0)
        self.xchg_msw2mod()
        has_converged = self.mf6.solve(sol_id)
        self.xchg_mod2msw()
        self.msw.finalize_solve(0)
        return has_converged

    def update_coupled(self):
        self.mf6.prepare_time_step(0.0)
        self.delt = self.mf6.get_time_step()
        self.msw.prepare_time_step(self.delt)

        # loop over subcomponents
        n_solutions = self.mf6.get_subcomponent_count()
        for sol_id in range(1, n_solutions + 1):

            # convergence loop
            kiter = 0
            self.mf6.prepare_solve(sol_id)
            while kiter < self.max_iter:
                has_converged = self.do_iter(sol_id)
                if has_converged:
                    logger.debug(f"Component {sol_id} converged in {kiter} iterations")
                    break
                kiter += 1
            self.mf6.finalize_solve(sol_id)

        self.mf6.finalize_time_step()
        current_time = self.mf6.get_current_time()
        self.msw_time = current_time
        self.msw.finalize_time_step()
        return current_time

    def getTimes(self):
        return (
            self.mf6.get_start_time(),
            self.mf6.get_current_time(),
            self.mf6.get_end_time(),
        )

    def report_timing_totals(self):
        if self.timing:
            total = self.mf6.report_timing_totals() + self.msw.report_timing_totals()
            logger.info(
                f"Total elapsed time in compiled libraries: {total:0.4f} seconds"
            )
            return total
        else:
            raise Exception("Timing not activated")

    def couple(self):
        mf6_modelname = self.get_mf6_modelname()
        self.mf6_head = self.mf6.get_value_ptr("SLN_1/X")
        self.mf6_recharge = self.mf6.get_value_ptr(
            mf6_modelname.upper() + " RCH-1/BOUND"
        )
        self.mf6_storage = self.mf6.get_value_ptr(mf6_modelname.upper() + " STO/SC2")
        self.ncell_mod = np.size(self.mf6_storage)
        self.ncell_recharge = np.size(self.mf6_recharge)
        self.max_iter = self.mf6.get_value_ptr("SLN_1/MXITER")[0]

        # get some 'pointers' to MF6 and MSW internal data
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

        # TODO: Fix the loops below, they are invalid and only work,
        # because the condition "if i in map_msw2mod" is never true.
        # Initalize the heads in MetaSWAP by copying them from MODFLOW
        self.xchg_mod2msw()
