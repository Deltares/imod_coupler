from typing import Any, Dict, Optional, Tuple

import numpy as np
from loguru import logger
from numpy.typing import NDArray
from scipy.sparse import csr_matrix, dia_matrix
from xmipy import XmiWrapper

from imod_coupler.utils import create_mapping


def unique_list(input):
    output = np.unique(np.array(input))
    return list(output)


# mapping different types of exchanges within DFLOWMETMOD driver
def mapping_active_MF_DFLOW1D(workdir, dflow1d_lookup, array: Optional[NDArray] = None):
    # function creates dictionary with mapping tables for mapping MF <-> dflow1d
    # mapping includes active MF coupling:
    #   1 MF RIV 1                      -> DFLOW-FM 1D flux
    #   2 DFLOW FM 1D (correction)flux  -> MF RIV 1
    #   3 DFLOW FM 1D stage             -> MF RIV 1
    map_active_mod_dflow1d: Dict[str, csr_matrix] = {}
    mask_active_mod_dflow1d: Dict[str, NDArray[Any]] = {}

    # MF RIV 1 -> DFLOW 1D (flux)
    mapping_file = workdir / "MFRIVTODFM1D_Q.DMM"
    if mapping_file.is_file():
        table_active_mfriv2dflow1d: NDArray[np.single] = np.loadtxt(
            mapping_file, dtype=np.single, ndmin=2, skiprows=1
        )
        mf_idx = table_active_mfriv2dflow1d[:, 2].astype(int) - 1
        dflow_idx = np.array(
            [
                dflow1d_lookup[
                    table_active_mfriv2dflow1d[ii, 0], table_active_mfriv2dflow1d[ii, 1]
                ]
                for ii in range(len(table_active_mfriv2dflow1d))
            ]
        )
        (
            map_active_mod_dflow1d["mf-riv2dflow1d_flux"],
            mask_active_mod_dflow1d["mf-riv2dflow1d_flux"],
        ) = create_mapping(
            mf_idx,
            dflow_idx,
            max(mf_idx) + 1,
            max(dflow_idx) + 1,
            "sum",
        )
        # DFLOW 1D  -> MF RIV 1 (flux)
        # weight array is flux-array from previous MF-RIV1 -> dlfowfm exchange
        weight = weight_from_flux_distribution(dflow_idx, mf_idx, array)
        (
            map_active_mod_dflow1d["dflow1d2mf-riv_flux"],
            mask_active_mod_dflow1d["dflow1d2mf-riv_flux"],
        ) = create_mapping(
            dflow_idx,
            mf_idx,
            max(dflow_idx) + 1,
            max(mf_idx) + 1,
            "weight",
            weight,
        )
    # DFLOW 1D -> MF RIV 1 (stage)
    mapping_file = workdir / "DFM1DWATLEVTOMFRIV_H.DMM"
    if mapping_file.is_file():
        table_active_dflow1d2mfriv: NDArray[np.single] = np.loadtxt(
            mapping_file, dtype=np.single, ndmin=2, skiprows=1
        )
        mf_idx = table_active_dflow1d2mfriv[:, 0].astype(int) - 1
        weight = table_active_dflow1d2mfriv[:, 3]
        dflow_idx = np.array(
            [
                dflow1d_lookup[
                    table_active_dflow1d2mfriv[ii, 1], table_active_dflow1d2mfriv[ii, 2]
                ]
                for ii in range(len(table_active_dflow1d2mfriv))
            ]
        )
        (
            map_active_mod_dflow1d["dflow1d2mf-riv_stage"],
            mask_active_mod_dflow1d["dflow1d2mf-riv_stage"],
        ) = create_mapping(
            dflow_idx,
            mf_idx,
            max(dflow_idx) + 1,
            max(mf_idx) + 1,
            "weight",
            weight,
        )
    return map_active_mod_dflow1d, mask_active_mod_dflow1d


def mapping_passive_MF_DFLOW1D(workdir, dflow1d_lookup):
    # function creates dictionary with mapping tables for mapping MF <-> dflow1d
    # mapping includes passive MF coupling:
    #   1 MF RIV 2                      -> DFLOW-FM 1D flux
    #   2 MF DRN                        -> DFLOW-FM 1D flux
    map_passive_mod_dflow1d: Dict[str, csr_matrix] = {}
    mask_passive_mod_dflow1d: Dict[str, NDArray[Any]] = {}

    # MF RIV 2 -> DFLOW 1D (flux)
    mapping_file = workdir / "MFRIV2TODFM1D_Q.DMM"
    if mapping_file.is_file():
        table_passive_mfriv2dflow1d: NDArray[np.single] = np.loadtxt(
            mapping_file, dtype=np.single, ndmin=2, skiprows=1
        )
        mf_idx = table_passive_mfriv2dflow1d[:, 2].astype(int) - 1
        dflow_idx = np.array(
            [
                dflow1d_lookup[
                    table_passive_mfriv2dflow1d[ii, 0],
                    table_passive_mfriv2dflow1d[ii, 1],
                ]
                for ii in range(len(table_passive_mfriv2dflow1d))
            ]
        )
        (
            map_passive_mod_dflow1d["mf-riv2dflow1d_flux"],
            mask_passive_mod_dflow1d["mf-riv2dflow1d_flux"],
        ) = create_mapping(
            mf_idx,
            dflow_idx,
            max(mf_idx) + 1,
            max(dflow_idx) + 1,
            "sum",
        )
    # MF DRN -> DFLOW 1D (flux)
    mapping_file = workdir / "MFDRNTODFM1D_Q.DMM"
    if mapping_file.is_file():
        table_passive_mfdrn2dflow1d: NDArray[np.single] = np.loadtxt(
            mapping_file, dtype=np.single, ndmin=2, skiprows=1
        )
        mf_idx = table_passive_mfdrn2dflow1d[:, 2].astype(int) - 1
        dflow_idx = np.array(
            [
                dflow1d_lookup[
                    table_passive_mfdrn2dflow1d[ii, 0],
                    table_passive_mfdrn2dflow1d[ii, 1],
                ]
                for ii in range(len(table_passive_mfdrn2dflow1d))
            ]
        )
        (
            map_passive_mod_dflow1d["mf-drn2dflow1d_flux"],
            mask_passive_mod_dflow1d["mf-drn2dflow1d_flux"],
        ) = create_mapping(
            mf_idx,
            dflow_idx,
            max(mf_idx) + 1,
            max(dflow_idx) + 1,
            "sum",
        )
    return map_passive_mod_dflow1d, mask_passive_mod_dflow1d


def mapping_MSW_DFLOW1D(workdir, dflow1d_lookup, array: Optional[NDArray] = None):
    # function creates dictionary with mapping tables for mapping MSW -> dflow1d
    # mapping includes MSW 1D coupling:
    #   1 MSW sprinkling flux            -> DFLOW-FM 1D flux
    #   2 DFLOW-FM 1D flux               -> MSW sprinkling flux
    #   3 MSW ponding flux               -> DFLOW-FM 1D flux (optional if no 2D network is availble)
    map_msw_dflow1d: Dict[str, csr_matrix] = {}
    mask_msw_dflow1d: Dict[str, NDArray[Any]] = {}

    # MSW -> DFLOW 1D (sprinkling)
    mapping_file = workdir / "MSWSPRINKTODFM1D_Q.DMM"
    if mapping_file.is_file():
        table_mswsprinkling2dflow1d: NDArray[np.single] = np.loadtxt(
            mapping_file, dtype=np.single, ndmin=2, skiprows=1
        )
        msw_idx = table_mswsprinkling2dflow1d[:, 2].astype(int) - 1
        dflow_idx = np.array(
            [
                dflow1d_lookup[
                    table_mswsprinkling2dflow1d[ii, 0],
                    table_mswsprinkling2dflow1d[ii, 1],
                ]
                for ii in range(len(table_mswsprinkling2dflow1d))
            ]
        )
        (
            map_msw_dflow1d["msw-sprinkling2dflow1d_flux"],
            mask_msw_dflow1d["msw-sprinkling2dflow1d_flux"],
        ) = create_mapping(
            msw_idx,
            dflow_idx,
            max(msw_idx) + 1,
            max(dflow_idx) + 1,
            "sum",
        )
        # DFLOW 1D -> MSW (sprinkling)
        weight = weight_from_flux_distribution(
            msw_idx, dflow_idx, array
        )  # array is flux-array from previous MSW-sprinkling -> dflowfm 1d
        (
            map_msw_dflow1d["dflow1d_flux2msw-sprinkling"],
            mask_msw_dflow1d["dflow1d_flux2msw-sprinkling"],
        ) = create_mapping(
            dflow_idx, msw_idx, len(dflow_idx), len(msw_idx), "weight", weight
        )
    # MSW -> DFLOW 1D (ponding)
    mapping_file = workdir / "MSWRUNOFFTODFM1D_Q.DMM"
    if mapping_file.is_file():
        table_mswponding2dflow1d: NDArray[np.single] = np.loadtxt(
            mapping_file, dtype=np.single, ndmin=2, skiprows=1
        )
        msw_idx = table_mswponding2dflow1d[:, 2].astype(int) - 1
        dflow_idx = np.array(
            [
                dflow1d_lookup[
                    table_mswponding2dflow1d[ii, 0], table_mswponding2dflow1d[ii, 1]
                ]
                for ii in range(len(table_mswponding2dflow1d))
            ]
        )
        (
            map_msw_dflow1d["msw-sprinkling2dflow1d_flux"],
            mask_msw_dflow1d["msw-sprinkling2dflow1d_flux"],
        ) = create_mapping(
            msw_idx,
            dflow_idx,
            max(msw_idx) + 1,
            max(dflow_idx) + 1,
            "sum",
        )
    return map_msw_dflow1d, mask_msw_dflow1d


def mapping_MSW_DFLOW2D(workdir, dflow2d_lookup, array: Optional[NDArray] = None):
    # dictionary with mapping tables for msw-dflow-2d coupling
    # mapping includes MSW 2D coupling:
    #   1 MSW ponding flux               -> DFLOW-FM 2D flux (optional)
    #   2 DFLOW-FM 2D flux               -> MSW ponding flux (optional)
    #   3 DFLOW-FM 2D stage              -> MSW ponding stage (optional)
    map_msw_dflow2d: Dict[str, csr_matrix] = {}
    mask_msw_dflow2d: Dict[str, NDArray[Any]] = {}

    # MSW -> DFLOW 2D (ponding)
    mapping_file = workdir / "MSWPONDINGTODFM2D_DV.DMM"
    if mapping_file.is_file():
        # ---mapping of msw poning to dflow2d---
        table_mswponding2dflow2d: NDArray[np.single] = np.loadtxt(
            mapping_file, dtype=np.single, ndmin=2, skiprows=1
        )
        msw_idx = table_mswponding2dflow2d[:, 2].astype(int) - 1
        dflow_idx = [
            dflow2d_lookup[
                table_mswponding2dflow2d[ii, 0], table_mswponding2dflow2d[ii, 1]
            ]
            for ii in range(len(table_mswponding2dflow2d))
        ]
        (
            map_msw_dflow2d["msw-ponding2dflow2d_flux"],
            mask_msw_dflow2d["msw-ponding2dflow2d_flux"],
        ) = create_mapping(
            msw_idx,
            dflow_idx,
            max(msw_idx) + 1,
            max(dflow_idx) + 1,
            "sum",
        )
        # DFLOW 2D -> MSW (ponding)
        # TODO: check if this is always, 1:1 connection, otherwise use weights
        (
            map_msw_dflow2d["dflow2d_flux2msw-ponding"],
            mask_msw_dflow2d["dflow2d_flux2msw-ponding"],
        ) = create_mapping(
            dflow_idx,
            msw_idx,
            max(dflow_idx) + 1,
            max(msw_idx) + 1,
            "sum",  # check TODO
        )
    # DFLOW 2D -> MSW (stage/innudation)
    mapping_file = workdir / " DFM2DWATLEVTOMSW_H.DMM"
    if mapping_file.is_file():
        table_dflow2d_stage2mswponding: NDArray[np.single] = np.loadtxt(
            mapping_file, dtype=np.single, ndmin=2, skiprows=1
        )
        msw_idx = table_dflow2d_stage2mswponding[:, 0] - 1
        weight = table_dflow2d_stage2mswponding[:, 3]
        dflow_idx = [
            dflow2d_lookup[
                table_dflow2d_stage2mswponding[ii, 1],
                table_dflow2d_stage2mswponding[ii, 2],
            ]
            for ii in range(len(table_dflow2d_stage2mswponding))
        ]
        (
            map_msw_dflow2d["dflow2d_stage2msw-ponding"],
            mask_msw_dflow2d["dflow2d_stage2msw-ponding"],
        ) = create_mapping(
            dflow_idx, msw_idx, len(dflow_idx), len(msw_idx), "weight", weight
        )


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


def test_weight_from_flux_distribution():
    # test calculated weights based on flux exchange
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
    return all(expected_weight == calculated_weight)


# read file with all uniek coupled dflow 1d and 2d nodes (represented by xy pairs). After initialisation
# of dflow, dict is filled with node-id's corresponding tot xy-pairs.
# this functions should be called after initialisation of dflow-fm.
def get_dflow1d_lookup(workdir):
    ok = True
    dflow1d_lookup = {}
    dflow1d_file = workdir / "DFLOWFM1D_POINTS.DAT"
    if dflow1d_file.is_file():
        dflow1d_data: NDArray[np.single] = np.loadtxt(
            dflow1d_file, dtype=np.single, ndmin=2, skiprows=1
        )
        dflow1d_x = dflow1d_data[:, 3]
        dflow1d_y = dflow1d_data[:, 4]
        # XMI/BMI call to dflow-fm with x and y list, returns id list with node numbers
        # dflowfm_MapCoordinateTo1DCellId(x, y, id)
        # for testing purpose, we take the id from the dat-file
        dflow1d_id = dflow1d_data[:, 1].astype(int) - 1
        ii = dflow1d_data.shape[0]
        for i in range(0, ii):
            if dflow1d_id[i] >= 0:
                dflow1d_lookup[(dflow1d_x[i], dflow1d_y[i])] = dflow1d_id[i]
            else:
                ValueError(
                    f"xy coordinate {dflow1d_x[i], dflow1d_y[i]} is not part of dflow's mesh"
                )
    else:
        print(f"Can't find {dflow1d_file}.")
        ok = False
    return dflow1d_lookup, ok


def get_dflow2d_lookup(workdir):
    ok = True
    dflow2d_lookup = {}
    dflow2d_file = workdir / "DFLOWFM2D_POINTS.DAT"
    if dflow2d_file.is_file():
        dflow2d_data: NDArray[np.single] = np.loadtxt(
            dflow2d_file, dtype=np.single, ndmin=2, skiprows=1
        )
        dflow2d_x = dflow2d_data[:, 3]
        dflow2d_y = dflow2d_data[:, 4]
        # XMI/BMI call to dflow-fm with x and y list, returns id list with node numbers
        # dflowfm_MapCoordinateTo2DCellId(x, y, id) -> id
        id = np.array([0])  # dummy array, check 0-indexing
        ii = id.shape[0]
        for i in ii:
            if id[i] > 0:
                dflow2d_lookup[(dflow2d_x[i], dflow2d_y[i])] = id[i]
            else:
                ValueError(
                    f"xy coordinate {dflow2d_x,dflow2d_y} is not part of dflow's mesh"
                )
    else:
        ok = False
    return dflow2d_lookup, ok


# temporary store mapper in this file
def create_mapping(
    src_idx: Any,
    tgt_idx: Any,
    nsrc: int,
    ntgt: int,
    operator: str,
    weight: Optional[NDArray] = None,
) -> Tuple[csr_matrix, NDArray[np.int_]]:
    """
    Create a mapping from source indexes to target indexes by constructing
    a sparse matrix of size (ntgt x nsrc) and creates a mask array with 0
    for mapped entries and 1 otherwise.
    The mask allows to update the target array without overwriting the unmapped
    entries with zeroes:

    target = mask * target + mapping * source

    Parameters
    ----------
    src_idx : int
        The indexes in the source array, zero-based
    tgt_idx : int
        The indexes in the target array, zero-based
    nsrc : int
        The number of entries in the source array
    ntgt : int
        The number of entries in the target array
    operator : str
       Indicating how n-1 mappings should be dealt
       with: "avg" for average, "sum" for sum.
       Operator does not affect 1-n couplings.

    Returns
    -------
    Tuple
        containing the mapping (csr_matrix) and a mask (numpy array)
    """
    if operator == "avg":
        cnt = np.zeros(max(tgt_idx) + 1)
        for i in range(len(tgt_idx)):
            cnt[tgt_idx[i]] += 1
        dat = np.array([1.0 / cnt[xx] for xx in tgt_idx])
    elif operator == "sum":
        dat = np.ones(tgt_idx.shape)
    elif operator == "weight":
        dat = weight
    else:
        raise ValueError("`operator` should be either 'sum', 'avg' or 'weight'")
    map_out = csr_matrix((dat, (tgt_idx, src_idx)), shape=(ntgt, nsrc))
    mask = np.array([0 if i > 0 else 1 for i in map_out.getnnz(axis=1)])
    return map_out, mask
