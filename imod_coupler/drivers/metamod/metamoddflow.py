#%%
from pathlib import Path
import numpy as np
from typing import Any, Dict

import numpy as np
from loguru import logger
from numpy.typing import NDArray
from scipy.sparse import csr_matrix, dia_matrix
from xmipy import XmiWrapper

workdir = Path(r"c:\src\lumbricus\lumbricustests\t-model\testA")


# this function calculates the weight based on the flux distribution of a n:1 connection,
# so it can be used in the 1:n redistribution of an correction flux or volume.
# Input is the target and source index of the mapings sparse array, and previouse flux array at n
# Output is weight-array for inversed mapping
def weight_from_flux_distribution(tgt_idx, src_idx, values):
    cnt = np.zeros(max(tgt_idx) + 1)
    weight = np.zeros(max(src_idx) + 1)
    for i in range(len(tgt_idx)):
        cnt[tgt_idx[i]] = cnt[tgt_idx[i]] + values[i]
    for i in range(len(tgt_idx)):
        weight[i] = values[i] / cnt[tgt_idx[i]]
    return weight


#%%
# read file with all uniek coupled dflow 1d and 2d nodes (represented by xy pairs). After initialisation
# of dflow, dict is filled with node-id's corresponding tot xy-pairs.
# this functions should be called after initialisation of dflow-fm.
dflow1d_lookup = {}
dflow1d_file = workdir / "dflow_nodes1d.dat"
if dflow1d_file.is_file():
    dflow1d_data: NDArray[np.float32] = np.loadtxt(
        dflow1d_file, dtype=np.int32, ndmin=2
    )
    dflow1d_x = dflow1d_file[:, 0]
    dflow1d_y = dflow1d_file[:, 1]
    # XMI/BMI call to dflow-fm with x and y list, returns id list with node numbers
    # dflowfm_MapCoordinateTo1DCellId(x, y, id)
    for i in id:
        if i > 0:
            dflow1d_lookup[(dflow1d_x[vi], dflow1d_y[vi])] = i
        else:
            ValueError(
                f"xy coordinate {dflow1d_x,dflow1d_y} is not part of dflow's mesh"
            )
else:
    raise ValueError(f"Can't find {dflow1d_file}.")


# read file with all uniek coupled dflow 1d and 2d nodes (represented by xy pairs). After initialisation
# of dflow, dict is filled with node-id's corresponding tot xy-pairs.
# this functions should be called after initialisation of dflow-fm.
dflow2d_lookup = {}
dflow2d_file = workdir / "dflow_nodes2d.dat"
if dflow2d_file.is_file():
    dflow2d_data: NDArray[np.float32] = np.loadtxt(
        dflow2d_file, dtype=np.int32, ndmin=2
    )
    dflow2d_x = dflow1d_file[:, 0]
    dflow2d_y = dflow1d_file[:, 1]
    # XMI/BMI call to dflow-fm with x and y list, returns id list with node numbers
    # dflowfm_MapCoordinateTo2DCellId(x, y, id)
    for i in id:
        if i > 0:
            dflow2d_lookup[(dflow2d_x[vi], dflow2d_y[vi])] = i
        else:
            ValueError(
                f"xy coordinate {dflow2d_x,dflow2d_y} is not part of dflow's mesh"
            )
else:
    raise ValueError(f"Can't find {dflow2d_file}.")

#%%
# dictionary with mapping tables for active mod-dflow-1d coupling
# mapping includes active MF coupling:
#   1 MF RIV 1                      -> DFLOW-FM 1D flux
#   2 DFLOW FM 1D (correction)flux  -> MF RIV 1
#   3 DFLOW FM 1D stage             -> MF RIV 1
map_active_mod_dflow1d: Dict[str, csr_matrix] = {}
mask_active_mod_dflow1d: Dict[str, NDArray[Any]] = {}

# dictionary with mapping tables for passive mod-dflow-1d coupling
# mapping includes passive MF coupling:
#   1 MF RIV 2                      -> DFLOW-FM 1D flux
#   2 MF DRN                        -> DFLOW-FM 1D flux
map_passive_mod_dflow1d: Dict[str, csr_matrix] = {}
mask_passive_mod_dflow1d: Dict[str, NDArray[Any]] = {}

# dictionary with mapping tables for msw-dflow-1d coupling
# mapping includes MSW 1D coupling:
#   1 MSW sprinkling flux            -> DFLOW-FM 1D flux
#   2 DFLOW-FM 1D flux               -> MSW sprinkling flux
#   3 MSW ponding flux               -> DFLOW-FM 1D flux (optional)
map_msw_dflow1d: Dict[str, csr_matrix] = {}
mask_msw_dflow1d: Dict[str, NDArray[Any]] = {}


# dictionary with mapping tables for msw-dflow-2d coupling
# mapping includes MSW 2D coupling:
#   1 MSW ponding flux               -> DFLOW-FM 2D flux (optional)
#   2 DFLOW-FM 2D flux               -> MSW ponding flux (optional)
#   3 DFLOW-FM 2D stage              -> MSW ponding stage (optional)
map_msw_dflow2d: Dict[str, csr_matrix] = {}
mask_msw_dflow2d: Dict[str, NDArray[Any]] = {}

#%%
# create mappings

# ---mapping of active coupled RIV-elements in MF to dflowfm1d nodes---
# mapping MF-RIV1 flux -> dflow1d
table_active_mfriv2dflow1d: NDArray[np.int32] = np.loadtxt(
    workdir / "MFRIVTODFM1D_Q.DMM", dtype=np.int32, ndmin=3
)
mf_idx = table_active_mfriv2dflow1d[:, 2] - 1
dflow_idx = [
    dflow1d_lookup[table_active_mfriv2dflow1d[ii, 0], table_active_mfriv2dflow1d[ii, 1]]
    for ii in range(len(table_active_mfriv2dflow1d))
]
(
    self.map_active_mod_dflow1d["mf-riv2dflow1d_flux"],
    self.mask_active_mod_dflow1d["mf-riv2dflow1d_flux"],
) = create_mapping(
    mf_idx,
    dflow_idx,
    len(mf_idx),
    len(dflow_idx),
    "sum",
)
# mapping dflowfm flux -> MF-RIV1
# for the correction flux exchange from dflow1d, the 'flux mapping' is used but in reversed direction. This is not equal to the
# head exchange from dflow1d to MF-RIV1.
weight = weight_from_flux_distribution(
    mf_idx, dflow_idx, array
)  # array is flux-array from previous MF-RIV1 -> dlfowfm
(
    self.map_active_mod_dflow1d["dflow1d2mf-riv_flux"],
    self.mask_active_mod_dflow1d["dflow1d2mf-riv_flux"],
) = create_mapping(
    dflow_idx,
    mf_idx,
    len(dflow_idx),
    len(mf_idx),
    "weight",
    weight,
)
# mapping dflow1d stage -> MF-RIV1
table_active_dflow1d2mfriv: NDArray[np.int32] = np.loadtxt(
    workdir / "DFM1DWATLEVTOMFRIV_H.DMM", dtype=np.int32, ndmin=4
)
mf_idx = table_active_dflow1d2mfriv[:, 0] - 1
weight = table_active_dflow1d2mfriv[:, 3]
dflow_idx = [
    dflow1d_lookup[table_active_dflow1d2mfriv[ii, 1], table_active_dflow1d2mfriv[ii, 2]]
    for ii in range(len(table_active_dflow1d2mfriv))
]
(
    self.map_active_mod_dflow1d["dflow1d2mf-riv_stage"],
    self.mask_active_mod_dflow1d["dflow1d2mf-riv_stage"],
) = create_mapping(
    dflow_idx,
    mf_idx,
    len(dflow_idx),
    len(mf_idx),
    "weight",
    weight,
)

# ---mapping of passive coupled RIV- and DRN-elements in MF to dflowfm1d nodes---
# mapping MF-RIV2 flux -> dflow1d
table_passive_mfriv2dflow1d: NDArray[np.int32] = np.loadtxt(
    workdir / "MFRIV2TODFM1D_Q.DMM", dtype=np.int32, ndmin=3
)
mf_idx = table_passive_mfriv2dflow1d[:, 2] - 1
dflow_idx = [
    dflow1d_lookup[
        table_passive_mfriv2dflow1d[ii, 0], table_passive_mfriv2dflow1d[ii, 1]
    ]
    for ii in range(len(table_passive_mfriv2dflow1d))
]
(
    self.map_passive_mod_dflow1d["mf-riv2dflow1d_flux"],
    self.mask_passive_mod_dflow1d["mf-riv2dflow1d_flux"],
) = create_mapping(
    mf_idx,
    dflow_idx,
    len(mf_idx),
    len(dflow_idx),
    "sum",
)
# mapping MF-DRN -> dflow1d
table_passive_mfdrn2dflow1d: NDArray[np.int32] = np.loadtxt(
    workdir / "MFDRNTODFM1D_Q.DMM", dtype=np.int32, ndmin=3
)
mf_idx = table_passive_mfdrn2dflow1d[:, 2] - 1
dflow_idx = [
    dflow1d_lookup[
        table_passive_mfdrn2dflow1d[ii, 0], table_passive_mfdrn2dflow1d[ii, 1]
    ]
    for ii in range(len(table_passive_mfdrn2dflow1d))
]
(
    self.map_passive_mod_dflow1d["mf-drn2dflow1d_flux"],
    self.mask_passive_mod_dflow1d["mf2-drn2dflow1d_flux"],
) = create_mapping(
    mf_idx,
    dflow_idx,
    len(mf_idx),
    len(dflow_idx),
    "sum",
)

# ---mapping of MSW to dflowfm1d nodes---
# mapping MSW-sprinkling -> dflow1d
table_mswsprinkling2dflow1d: NDArray[np.int32] = np.loadtxt(
    workdir / "MSWSPRINKTODFM1D_Q.DMS", dtype=np.int32, ndmin=3
)
msw_idx = table_mswsprinkling2dflow1d[:, 2] - 1
dflow_idx = [
    dflow1d_lookup[
        table_mswsprinkling2dflow1d[ii, 0], table_mswsprinkling2dflow1d[ii, 1]
    ]
    for ii in range(len(table_mswsprinkling2dflow1d))
]
(
    self.map_msw_dflow1d["msw-sprinkling2dflow1d_flux"],
    self.mask_msw_dflow1d["msw-sprinkling2dflow1d_flux"],
) = create_mapping(
    msw_idx,
    dflow_idx,
    len(mf_idx),
    len(dflow_idx),
    "sum",
)
# mapping of returnflux from dflow1d -> msw, based on fraction of deleverd flux distribution
weight = weight_from_flux_distribution(
    msw_idx, dflow_idx, array
)  # array is flux-array from previous MSW-sprinkling -> dflowfm 1d
(
    self.map_msw_dflow1d["dflow1d_flux2msw-sprinkling"],
    self.mask_msw_dflow1d["dflow1d_flux2msw-sprinkling"],
) = create_mapping(dflow_idx, msw_idx, len(dflow_idx), len(mf_idx), "weight", weight)
# mapping of msw poning to dflow1d (optional if 2d network is not availble). In this case no return flux to msw
table_mswponding2dflow1d: NDArray[np.int32] = np.loadtxt(
    workdir / "MSWRUNOFFTODFM1D_Q.DMM  ", dtype=np.int32, ndmin=3
)
if table_mswponding2dflow1d.is_file():
    msw_idx = table_mswponding2dflow1d[:, 2] - 1
    dflow_idx = [
        dflow1d_lookup[table_mswponding2dflow1d[ii, 0], table_mswponding2dflow1d[ii, 1]]
        for ii in range(len(table_mswponding2dflow1d))
    ]
    (
        self.map_msw_dflow1d["msw-sprinkling2dflow1d_flux"],
        self.mask_msw_dflow1d["msw-sprinkling2dflow1d_flux"],
    ) = create_mapping(
        msw_idx,
        dflow_idx,
        len(mf_idx),
        len(dflow_idx),
        "sum",
    )
# ---mapping of msw poning to dflow2d---
table_mswponding2dflow2d: NDArray[np.int32] = np.loadtxt(
    workdir / "MSWPONDINGTODFM2D_DV.DMM", dtype=np.int32, ndmin=3
)
if table_mswponding2dflow2d.is_file():
    msw_idx = table_mswponding2dflow2d[:, 2] - 1
    dflow_idx = [
        dflow2d_lookup[table_mswponding2dflow2d[ii, 0], table_mswponding2dflow2d[ii, 1]]
        for ii in range(len(table_mswponding2dflow2d))
    ]
    (
        self.map_msw_dflow2d["msw-ponding2dflow2d_flux"],
        self.mask_msw_dflow2d["msw-ponding2dflow2d_flux"],
    ) = create_mapping(
        msw_idx,
        dflow_idx,
        len(mf_idx),
        len(dflow_idx),
        "sum",
    )
    # mapping of returnflux from dflow1d -> msw, no fraction nedded because of 1:1 connection
    (
        self.map_msw_dflow2d["dflow2d_flux2msw-ponding"],
        self.mask_msw_dflow2d["dflow2d_flux2msw-ponding"],
    ) = create_mapping(
        dflow_idx,
        msw_idx,
        len(dflow_idx),
        len(mf_idx),
        "sum",  # 1:1 connection, should be no other weight than 1
    )
    table_dflow2d_stage2mswponding: NDArray[np.int32] = np.loadtxt(
        workdir / " DFM2DWATLEVTOMSW_H.DMM", dtype=np.int32, ndmin=3
    )
    msw_idx = table_dflow2d_stage2mswponding[:, 0] - 1
    weight = table_dflow2d_stage2mswponding[:, 3]
    dflow_idx = [
        dflow2d_lookup[
            table_dflow2d_stage2mswponding[ii, 1], table_dflow2d_stage2mswponding[ii, 2]
        ]
        for ii in range(len(table_dflow2d_stage2mswponding))
    ]
    (
        self.map_msw_dflow2d["dflow2d_stage2msw-ponding"],
        self.mask_msw_dflow2d["dflow2d_stage2msw-ponding"],
    ) = create_mapping(
        dflow_idx, msw_idx, len(dflow_idx), len(mf_idx), "weight", weight
    )

# exmaple how actual exchange would look like
# TODO: check BMI calls and functionalities, check units conversions
def exchange_mod2dflow1d(self) -> None:
    """Exchange MODFLOW to DFLOW 1d"""
    self.mf_riv_flux[:] = (
        self.mask_active_mod_dflow1d["mf-riv2dflow1d_flux"][:] * self.mf6_riv_flux[:]
        + self.map_active_mod_dflow1d["mf-riv2dflow1d_flux"].dot(self.dflow1d_flux)[:]
    )


def exchange_dflow1d2mod(self) -> None:
    """Exchange DFLOW 1d to MODFLOW"""
    self.dflow1d_stage[:] = (
        self.mask_active_mod_dflow1d["dflow1d2mf-riv_stage"][:] * self.dflow1d_stage[:]
        + self.map_active_mod_dflow1d["dflow1d2mf-riv_stage"].dot(self.mf6_riv_stage)[:]
    )
    self.dflow1d_flux[:] = (
        self.mask_active_mod_dflow1d["dflow1d2mf-riv_flux"][:] * self.dflow1d_flux[:]
        + self.map_active_mod_dflow1d["dflow1d2mf-riv_flux"].dot(self.mf6_riv_flux)[:]
    )


#%%
# unit-test calculated weights based on flux exchange
# mf-riv1 elements=5
# dfow1d  elements=3

# set dummy variables
# previous flux from MF-RIV1 to DFLOW1d
dummy_flux_mf2dflow1d = np.array([1, 2, 3, 4, 5])
# set connection sparse array for DFLOW1d --> MF
target_index = np.array([0, 0, 1, 1, 2])
source_index = np.array([0, 1, 2, 3, 4])

# evaluate weight distribution
expected_weight = np.array([1 / 3, 2 / 3, 3 / 7, 4 / 7, 5 / 5])
calculated_weight = weight_from_flux_distribution(
    target_index, source_index, dummy_flux_mf2dflow1d
)

if all(expected_weight == calculated_weight):
    print("unittest 1 passed")

# unit-test exchange flux from dflow1d to mf based on flux distribution of previous mf -> dflow1d flux exchange
# use previously used connection
target_index = np.array([0, 0, 1, 1, 2])
source_index = np.array([0, 1, 2, 3, 4])

# previous flux from MF-RIV1 to DFLOW1d
dummy_flux_mf2dflow1d = np.array([1, 2, 3, 4, 5])
# create dummy flux-file for exchange DFLOW1d to MF RIV1
dummy_flux_flow1d2MF = np.array([1, 2, 3])

# calcluate weight distribution
weight = weight_from_flux_distribution(
    target_index, source_index, dummy_flux_mf2dflow1d
)

# expected exchange flux at MF-RIV1 nodes
expected_exchange_flux = np.array(
    [1 * weight[0], 1 * weight[1], 2 * weight[2], 2 * weight[3], 3 * weight[4]]
)

#%%
