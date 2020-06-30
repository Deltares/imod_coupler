#!/usr/bin/env python
import sys
import os
import json
import numpy as np
from amipy import AmiWrapper
import logging


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
    map_arr = np.loadtxt(map_file, dtype=str, delimiter=',')
    for sgw, ssv in map_arr:
        gw = int(sgw)-1
        sv = int(ssv.replace("'","").split()[0])
        map_in.setdefault(gw, []).append(sv-1)
    return map_in


def read_mapping_json(map_file):  # json-style input couple
    try:
        fmap = open(map_file, "r")
    except Exception as e:
        sys.stderr.write("Opening mapping file '" + map_file + "' failed !\n")
        sys.stderr.write(str(e))
        return {}
    map_in = {}
    cnt = 0
    for line in fmap.readlines():
        cnt = cnt + 1
        try:
            json_dict = json.loads(line)
        except Exception as e:
            sys.stderr.write("Parsing error in line %d ..." % cnt)
            sys.stderr.write("%s" % line)
            sys.stderr.write(str(e))
        mswlist = json_dict["msw"]
        mf6list = json_dict["mf6"]
        for gw in mf6list:
            if gw not in map_in:
                map_in[gw] = []
            for sv in mswlist:
                map_in[gw].append(sv)
    fmap.close()
    for gw in map_in.keys():
        map_in[gw] = list(set(map_in[gw]))
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


class MetaMod(AmiWrapper):
    def __init__(self, **kwargs):
        mf6_dll = kwargs["mf6_dll"]
        msw_dll = kwargs["msw_dll"]
        mf6_modeldir = kwargs["mf6_modeldir"]
        msw_modeldir = kwargs["msw_modeldir"]

        super().__init__(mf6_dll)
        self.working_directory = mf6_modeldir
        mf6_config_file = os.path.join(mf6_modeldir, "mfsim.nam")
        self.set_int("ISTDOUTTOFILE", 0)
        self.initialize(mf6_config_file)

        # extract the model name from the the mf6_config_file
        mfsim_name = os.path.join(self.working_directory, "mfsim.nam")
        mfsim = open(mfsim_name, "r")
        mfsim_lines = mfsim.readlines()
        mfsim.close()
        for ndx, line in enumerate(mfsim_lines):
            if "BEGIN MODELS" in line:
                modeltype, modelnamfile, modelname = mfsim_lines[ndx + 1].split()
                break

        self.mf6_head = self.get_value_ptr("SLN_1/X")
        self.mf6_recharge = self.get_value_ptr(modelname.upper() + " RCH-1/BOUND")
        self.mf6_storage = self.get_value_ptr(modelname.upper() + " STO/SC2")
        self.ncell_mod = np.size(self.mf6_storage)
        self.ncell_recharge = np.size(self.mf6_recharge)
        self.max_iter = self.get_value_ptr("SLN_1/MXITER")[0]

        self.couple(msw_dll, msw_modeldir)

    def xchg_msw2mod(self):
        for i in range(self.ncell_mod):
            if i in self.map_mod2msw["storage"]:
                self.mf6_storage[i] = np.sum(
                    self.msw_storage[self.map_mod2msw["storage"][i]]
                )
        for i in range(self.ncell_recharge):
            if i in self.map_mod2msw["recharge"]:
                # Divide by delta time, since Metaswap only keeps track of volumes
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
        has_converged = self.solve(sol_id)
        self.xchg_mod2msw()
        self.msw.finalize_solve(0)
        return has_converged

    def do_time_step(self):
        self.prepare_time_step(0.0)
        self.delt = self.get_time_step()
        self.msw.prepare_time_step(self.delt)

        # loop over subcomponents
        n_solutions = self.get_subcomponent_count()
        for sol_id in range(1, n_solutions + 1):

            # convergence loop
            kiter = 0
            self.prepare_solve(sol_id)
            while kiter < self.max_iter:
                has_converged = self.do_iter(sol_id)
                if has_converged:
                    logging.info(
                        "\n\nComponent ",
                        sol_id,
                        " converged in ",
                        kiter,
                        "iterations\n",
                    )
                    break
                kiter += 1
            self.finalize_solve(sol_id)

        self.finalize_time_step()
        current_time = self.get_current_time()
        self.msw_time = current_time
        self.msw.finalize_time_step()
        return current_time

    def getTimes(self):
        return self.get_start_time(), self.get_current_time(), self.get_end_time()

    def couple(self, msw_dll, msw_modeldir):
        # Load and init MetaSWAP
        self.msw = AmiWrapper(msw_dll)
        self.msw.working_directory = msw_modeldir
        self.msw.initialize(
            "config_file"
        )  # config file is a dummy argument, not used by msw

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
            sys.stderr.write("Missing mod2svat.inp")
            sys.exit(-1)
        map_msw2mod["head"] = invert_mapping(map_mod2msw["storage"])
        self.map_msw2mod = map_msw2mod
        self.map_mod2msw = map_mod2msw

        mapping_file_recharge = os.path.join(
            self.msw.working_directory, "mod2svat_recharge.inp"
        )
        if os.path.isfile(mapping_file_recharge):
            map_mod2msw["recharge"] = read_mapping(mapping_file_recharge)
        else:
            sys.stderr.write("Missing mod2svat_recharge.inp")
            sys.exit(-1)

        self.map_mod2msw = map_mod2msw
        self.map_msw2map = map_msw2mod

        # TODO: Fix the loops below, they are invalid and only work,
        # because the condition "if i in map_msw2mod" is never true.
        # Initalize the heads in MetaSWAP by copying them from MODFLOW
        self.xchg_mod2msw()

