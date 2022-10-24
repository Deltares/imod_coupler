#%%
from math import isclose
from pathlib import Path

import numpy as np
from mapping_functions import *


def calculated_as_expected(expected, calculated):
    ok = []
    for i in range(len(expected)):
        ok.append(isclose(expected[i], calculated[i], rel_tol=0.001, abs_tol=0.0))
    return all(ok)


workdir = Path(r"c:\src\imod_coupler\examples\input_example_mapping")

# Test exchange MF-DFLOW1D
# create dummy arrays to exchange

# mf riv1-flux to exchange
mf_riv1_flux = np.array([3, 3, 4, 4, 4])
# dflow1d flux and stage to exchange
dflow1d_flux = np.array([6, 7, 8])
dflow1d_stage = np.array([4, 5, 6])

# get dflow-id based on xy-coordinates after initialisation (now as test from file)
dflow1d_lookup, ok_file = get_dflow1d_lookup(workdir)

# create mapping for mf-dflow1d
# there is no previous flux geven for weight distributed weights,
# so DFLOW 1D stage -> MF RIV 1 exchange is not availble at this time
map_active_mod_dflow1d, mask_active_mod_dflow1d = mapping_active_MF_DFLOW1D(
    workdir, dflow1d_lookup
)

#%%
# exchange in order of actual coupling

# DFLOW 1D stage -> MF RIV 1 stage
# weighted averaging based on input files:
# dflow1d_nodes=((5,5),(25,15),(45,25))
# riv-id  fm-x    fm-y   weight    dflow-stage
#   1     5       5      0.9       4
#   1     25      15     0.1       5
#   2     5       5      0.450     4
#   2     25      15     0.550     5
#   3     5       5      0.950     4
#   3     25      15     0.050     5
#   4     25      15     0.40      5
#   4     45      25     0.60      6
#   5     25      15     0.1       5
#   5     45      25     0.9       6

mf_riv1_stage_receive_expected = np.array(
    [
        (0.9 * 4) + (0.1 * 5),
        (0.45 * 4) + (0.55 * 5),
        (0.95 * 4) + (0.05 * 5),
        (0.4 * 5) + (0.6 * 6),
        (0.1 * 5) + (0.9 * 6),
    ]
)
mf_riv1_stage_receive = np.array([0, 0, 0, 0, 0])
mf_riv1_stage_receive = (
    mask_active_mod_dflow1d["dflow1d2mf-riv_stage"][:] * mf_riv1_stage_receive[:]
    + map_active_mod_dflow1d["dflow1d2mf-riv_stage"].dot(dflow1d_stage)[:]
)
if not calculated_as_expected(mf_riv1_stage_receive_expected, mf_riv1_stage_receive):
    print("FOUT in exchange stage DFLOW 1D -> MF")

# MF RIV 1 -> DFLOW 1D flux
# flux is always n:1, so values are summed
dflow1d_flux_receive_expected = np.array([3 + 3, 4, 4 + 4])
dflow1d_flux_receive = np.array([0, 0, 0])
dflow1d_flux_receive = (
    mask_active_mod_dflow1d["mf-riv2dflow1d_flux"][:] * dflow1d_flux_receive[:]
    + map_active_mod_dflow1d["mf-riv2dflow1d_flux"].dot(mf_riv1_flux)[:]
)
if not calculated_as_expected(dflow1d_flux_receive_expected, dflow1d_flux_receive):
    print("FOUT in exchange flux MF -> DFLOW 1D")

# DFLOW 1D flux -> MF RIV 1 flux
# flux is always 1:n, decomposition based on previous Mf -> DFLOW flux distribution

# create new mapping based on  previous MF -> dflow flux exchange distribution
# for now, all mappingfiles are read in again, this could be optimised in the future
map_active_mod_dflow1d, mask_active_mod_dflow1d = mapping_active_MF_DFLOW1D(
    workdir, dflow1d_lookup, mf_riv1_flux
)
# expected results
weights = np.array([3 / 6, 3 / 6, 4 / 4, 4 / 8, 4 / 8])
mf_riv1_flux_receive_expected = np.array(
    [6 * weights[0], 6 * weights[1], 7 * weights[2], 8 * weights[3], 8 * weights[0]]
)
mf_riv1_flux_receive = np.array([0, 0, 0, 0, 0])
mf_riv1_flux_receive = (
    mask_active_mod_dflow1d["dflow1d2mf-riv_flux"][:] * mf_riv1_flux_receive[:]
    + map_active_mod_dflow1d["dflow1d2mf-riv_flux"].dot(dflow1d_flux)[:]
)
if not calculated_as_expected(mf_riv1_flux_receive_expected, mf_riv1_flux_receive):
    print("FOUT in exchange flux DFLOW 1D -> MF")

# mapping from dflow 1d to mf riv1 (weight based on weights inputfile)
def exchange_mod_dflow1d(self) -> None:
    """Exchange MODFLOW flux to DFLOW 1d"""
    self.mf_riv_flux[:] = (
        mask_active_mod_dflow1d["mf-riv2dflow1d_flux"][:] * self.mf6_riv_flux[:]
        + map_active_mod_dflow1d["mf-riv2dflow1d_flux"].dot(self.dflow1d_flux)[:]
    )


#%%
