from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
from numpy import float_, int_
from numpy.typing import NDArray
from scipy.sparse import csr_matrix, diags

from imod_coupler.utils import Operator, create_mapping


# mapping different types of exchanges within DFLOWMETMOD driver
def mapping_active_mf_dflow1d(
    mapping_file_mf6_river_to_dfm_1d_q: Path,
    mapping_file_dfm_1d_waterlevel_to_mf6_river_stage: Path,
    dflow1d_lookup: dict[tuple[float, float], int],
    weights: Optional[NDArray[float_]] = None,
) -> tuple[dict[str, csr_matrix], dict[str, NDArray[int_]]]:
    """
    function creates dictionary with mapping tables for mapping arrays between MF and dflow1d
    (both ways).

        # mapping includes active MF coupling:
        #   1 MF RIV 1                      -> DFLOW-FM 1D flux
        #   2 DFLOW FM 1D (correction)flux  -> MF RIV 1
        #   3 DFLOW FM 1D stage             -> MF RIV 1

    Parameters
    ----------
    mapping_file_mf6_river_to_dfm_1d_q : Path
        path of mapping file mf6 river nodes to dfm 1d  nodes
    mapping_file_dfm_1d_waterlevel_to_mf6_river_stage : Path
        path of mapping file dfm 1d  nodes to mf6 river nodes
    dflow1d_lookup : dict[tuple[float, float], int]
        used for mapping x, y coordinates to dflow node numbers
    array : Optional[NDArray[float_]], optional
        optional array for weigths

    Returns
    -------
    tuple[dict[str, csr_matrix], dict[str, NDArray[int_]]]
        The first return value is a dict containing as key, the exchange type,
        and as value, the sparse matrix used for this kind of exchange.
        The second return value is a dict containing as key, the exchange type,
        and as value, the mask used for this kind of exchange.

    """
    #
    map_active_mod_dflow1d: Dict[str, csr_matrix] = {}
    mask_active_mod_dflow1d: Dict[str, NDArray[Any]] = {}

    # MF RIV 1 -> DFLOW 1D (flux)
    table_active_mfriv2dflow1d: NDArray[np.single] = np.loadtxt(
        mapping_file_mf6_river_to_dfm_1d_q, dtype=np.single, ndmin=2, skiprows=1
    )
    mf_idx = table_active_mfriv2dflow1d[:, 2].astype(int) - 1
    dflow_idx = np.array(
        [dflow1d_lookup[row[0], row[1]] for row in table_active_mfriv2dflow1d]
    )
    (
        map_active_mod_dflow1d["mf-riv2dflow1d_flux"],
        mask_active_mod_dflow1d["mf-riv2dflow1d_flux"],
    ) = create_mapping(
        mf_idx,
        dflow_idx,
        max(mf_idx) + 1,
        max(dflow_idx) + 1,
        Operator.SUM,
    )
    # DFLOW 1D  -> MF RIV 1 (flux)
    # weight array is flux-array from previous MF-RIV1 -> dlfowfm exchange
    # if no weight array is provided, skip this exchange
    if weights is not None:
        weight = weight_from_flux_distribution(dflow_idx, mf_idx, weights)
        (
            map_active_mod_dflow1d["dflow1d2mf-riv_flux"],
            mask_active_mod_dflow1d["dflow1d2mf-riv_flux"],
        ) = create_mapping(
            dflow_idx,
            mf_idx,
            max(dflow_idx) + 1,
            max(mf_idx) + 1,
            Operator.WEIGHT,
            weight,
        )
    else:    
        (
            map_active_mod_dflow1d["dflow1d2mf-riv_flux"],
            mask_active_mod_dflow1d["dflow1d2mf-riv_flux"],
        ) = create_mapping(
            dflow_idx,
            mf_idx,
            max(dflow_idx) + 1,
            max(mf_idx) + 1,
            Operator.SUM
        )

    # DFLOW 1D -> MF RIV 1 (stage)
    table_active_dflow1d2mfriv: NDArray[np.single] = np.loadtxt(
        mapping_file_dfm_1d_waterlevel_to_mf6_river_stage,
        dtype=np.single,
        ndmin=2,
        skiprows=1,
    )
    mf_idx = table_active_dflow1d2mfriv[:, 0].astype(int) - 1
    weight = table_active_dflow1d2mfriv[:, 3]
    dflow_idx = np.array(
        [dflow1d_lookup[row[1], row[2]] for row in table_active_dflow1d2mfriv]
    )
    (
        map_active_mod_dflow1d["dflow1d2mf-riv_stage"],
        mask_active_mod_dflow1d["dflow1d2mf-riv_stage"],
    ) = create_mapping(
        dflow_idx,
        mf_idx,
        max(dflow_idx) + 1,
        max(mf_idx) + 1,
        Operator.WEIGHT,
        weight,
    )
    return map_active_mod_dflow1d, mask_active_mod_dflow1d


def mapping_passive_mf_dflow1d(
    mf6_river2_to_dmf_1d_q_dmm: Path,
    mf6_drainage_to_dfm_1d_q_dmm: Path,
    dflow1d_lookup: dict[tuple[float, float], int],
) -> tuple[dict[str, csr_matrix], dict[str, NDArray[int_]]]:
    """
    function creates dictionary with mapping tables for mapping MF <-> dflow1d
    To be used for passive MF coupling:
      1 MF RIV 2                      -> DFLOW-FM 1D flux
      2 MF DRN                        -> DFLOW-FM 1D flux

    Parameters
    ----------
    workdir : Path
        directory where mapping-related input files can be found
    dflow1d_lookup : dict[tuple[float, float], int]
        used for mapping x, y coordinates to dflow node numbers

    Returns
    -------
    tuple[dict[str, csr_matrix], dict[str, NDArray[int_]]]
        The first return value is a dict containing as key, the exchange type,
        and as value, the sparse matrix used for this kind of exchange.
        The second return value is a dict containing as key, the exchange type,
        and as value, the mask used for this kind of exchange.
    """

    map_passive_mod_dflow1d: Dict[str, csr_matrix] = {}
    mask_passive_mod_dflow1d: Dict[str, NDArray[Any]] = {}

    # MF RIV 2 -> DFLOW 1D (flux)
    table_passive_mfriv2dflow1d: NDArray[np.single] = np.loadtxt(
        mf6_river2_to_dmf_1d_q_dmm, dtype=np.single, ndmin=2, skiprows=1
    )
    mf_idx = table_passive_mfriv2dflow1d[:, 2].astype(int) - 1
    dflow_idx = np.array(
        [dflow1d_lookup[row[0], row[1]] for row in table_passive_mfriv2dflow1d]
    )
    (
        map_passive_mod_dflow1d["mf-riv2dflow1d_flux"],
        mask_passive_mod_dflow1d["mf-riv2dflow1d_flux"],
    ) = create_mapping(
        mf_idx,
        dflow_idx,
        max(mf_idx) + 1,
        max(dflow_idx) + 1,
        Operator.SUM,
    )
    # MF DRN -> DFLOW 1D (flux)
    table_passive_mfdrn2dflow1d: NDArray[np.single] = np.loadtxt(
        mf6_drainage_to_dfm_1d_q_dmm, dtype=np.single, ndmin=2, skiprows=1
    )
    mf_idx = table_passive_mfdrn2dflow1d[:, 2].astype(int) - 1
    dflow_idx = np.array(
        [dflow1d_lookup[row[0], row[1]] for row in table_passive_mfdrn2dflow1d]
    )
    (
        map_passive_mod_dflow1d["mf-drn2dflow1d_flux"],
        mask_passive_mod_dflow1d["mf-drn2dflow1d_flux"],
    ) = create_mapping(
        mf_idx,
        dflow_idx,
        max(mf_idx) + 1,
        max(dflow_idx) + 1,
        Operator.SUM,
    )
    return map_passive_mod_dflow1d, mask_passive_mod_dflow1d


def mapping_msw_dflow1d(
    msw_runoff_to_dfm_1d_q_dmm: Path,
    msw_sprinkling_to_dfm_1d_q_dmm: Path,
    dflow1d_lookup: dict[tuple[float, float], int],
    msw_sprinkling_flux: Optional[NDArray[float_]] = None,
) -> tuple[dict[str, csr_matrix], dict[str, NDArray[int_]]]:

    """
    function creates dictionary with mapping tables for mapping MSW -> dflow1d
    mapping includes MSW 1D coupling:
    1 MSW sprinkling flux            -> DFLOW-FM 1D flux
    2 DFLOW-FM 1D flux               -> MSW sprinkling flux
    3 MSW ponding flux               -> DFLOW-FM 1D flux (optional if no 2D network is availble)

    workdir : Path
        directory where mapping-related input files can be found
    dflow1d_lookup : dict[tuple[float, float], int]
        used for mapping x, y coordinates to dflow node numbers
    msw_sprinkling_flux: Optional[NDArray[float_]]
        flux-array from previous MSW-sprinkling -> dflowfm 1d


    Returns
    -------
        The first return value is a dict containing as key, the exchange type,
        and as value, the sparse matrix used for this kind of exchange.
        The second return value is a dict containing as key, the exchange type,
        and as value, the mask used for this kind of exchange.
    """
    map_msw_dflow1d: Dict[str, csr_matrix] = {}
    mask_msw_dflow1d: Dict[str, NDArray[int_]] = {}

    # MSW -> DFLOW 1D (sprinkling)
    table_mswsprinkling2dflow1d: NDArray[np.single] = np.loadtxt(
        msw_sprinkling_to_dfm_1d_q_dmm, dtype=np.single, ndmin=2, skiprows=1
    )
    msw_idx = table_mswsprinkling2dflow1d[:, 2].astype(int) - 1

    dflow_idx = np.array(
        [dflow1d_lookup[row[0], row[1]] for row in table_mswsprinkling2dflow1d]
    )
    (
        map_msw_dflow1d["msw-sprinkling2dflow1d_flux"],
        mask_msw_dflow1d["msw-sprinkling2dflow1d_flux"],
    ) = create_mapping(
        msw_idx,
        dflow_idx,
        max(msw_idx) + 1,
        max(dflow_idx) + 1,
        Operator.SUM,
    )
    if msw_sprinkling_flux is not None:
        # DFLOW 1D -> MSW (sprinkling)
        weight = weight_from_flux_distribution(msw_idx, dflow_idx, msw_sprinkling_flux)
        (
            map_msw_dflow1d["dflow1d_flux2msw-sprinkling"],
            mask_msw_dflow1d["dflow1d_flux2msw-sprinkling"],
        ) = create_mapping(
            dflow_idx,
            msw_idx,
            len(dflow_idx),
            len(msw_idx),
            Operator.WEIGHT,
            weight,
        )
    # MSW -> DFLOW 1D (ponding)
    table_mswponding2dflow1d: NDArray[np.single] = np.loadtxt(
        msw_runoff_to_dfm_1d_q_dmm, dtype=np.single, ndmin=2, skiprows=1
    )
    msw_idx = table_mswponding2dflow1d[:, 2].astype(int) - 1

    dflow_idx = np.array(
        [dflow1d_lookup[row[0], row[1]] for row in table_mswponding2dflow1d]
    )
    (
        map_msw_dflow1d["msw-sprinkling2dflow1d_flux"],
        mask_msw_dflow1d["msw-sprinkling2dflow1d_flux"],
    ) = create_mapping(
        msw_idx,
        dflow_idx,
        max(msw_idx) + 1,
        max(dflow_idx) + 1,
        Operator.SUM,
    )
    return map_msw_dflow1d, mask_msw_dflow1d


def mapping_msw_dflow2d(
    msw_ponding_to_dfm_2d_dv_dmm: Path,
    dfm_2d_waterlevels_to_msw_h_dmm: Path,
    dflow2d_lookup: dict[tuple[float, float], int],
) -> tuple[dict[str, csr_matrix], dict[str, NDArray[int_]]]:
    """
    # dictionary with mapping tables for msw-dflow-2d coupling
    # mapping includes MSW 2D coupling:
    #   1 MSW ponding flux               -> DFLOW-FM 2D flux (optional)
    #   2 DFLOW-FM 2D flux               -> MSW ponding flux (optional)
    #   3 DFLOW-FM 2D stage              -> MSW ponding stage (optional)

    Parameters
    ----------
    workdir : Path
        directory where mapping-related input files can be found
    dflow2d_lookup : dict[tuple[float, float], int]
        used for mapping x, y coordinates to dflow node numbers

    Returns
    -------
        The first return value is a dict containing as key, the exchange type,
        and as value, the sparse matrix used for this kind of exchange.
        The second return value is a dict containing as key, the exchange type,
        and as value, the mask used for this kind of exchange.
    """

    map_msw_dflow2d: Dict[str, csr_matrix] = {}
    mask_msw_dflow2d: Dict[str, NDArray[Any]] = {}

    # MSW -> DFLOW 2D (ponding)

    # ---mapping of msw poning to dflow2d---
    table_mswponding2dflow2d: NDArray[np.single] = np.loadtxt(
        msw_ponding_to_dfm_2d_dv_dmm, dtype=np.single, ndmin=2, skiprows=1
    )
    msw_idx = table_mswponding2dflow2d[:, 2].astype(int) - 1
    dflow_idx = np.array(
        [dflow2d_lookup[row[0], row[1]] for row in table_mswponding2dflow2d]
    )

    (
        map_msw_dflow2d["msw-ponding2dflow2d_flux"],
        mask_msw_dflow2d["msw-ponding2dflow2d_flux"],
    ) = create_mapping(
        msw_idx,
        dflow_idx,
        max(msw_idx) + 1,
        max(dflow_idx) + 1,
        Operator.SUM,
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
        Operator.SUM,  # check TODO
    )
    # DFLOW 2D -> MSW (stage/innudation)
    table_dflow2d_stage2mswponding: NDArray[np.single] = np.loadtxt(
        dfm_2d_waterlevels_to_msw_h_dmm, dtype=np.single, ndmin=2, skiprows=1
    )
    msw_idx = (table_dflow2d_stage2mswponding[:, 0] - 1).astype(int)
    weight = table_dflow2d_stage2mswponding[:, 3]
    dflow_idx = np.array(
        [
            dflow2d_lookup[
                table_dflow2d_stage2mswponding[ii, 1],
                table_dflow2d_stage2mswponding[ii, 2],
            ]
            for ii in range(len(table_dflow2d_stage2mswponding))
        ]
    )
    (
        map_msw_dflow2d["dflow2d_stage2msw-ponding"],
        mask_msw_dflow2d["dflow2d_stage2msw-ponding"],
    ) = create_mapping(
        dflow_idx, msw_idx, len(dflow_idx), len(msw_idx), Operator.WEIGHT, weight
    )
    return map_msw_dflow2d, mask_msw_dflow2d


def map_values_reweighted(
    mapping: csr_matrix, xin: NDArray[float_], rw: NDArray[float_]
) -> NDArray[float_]:
    """
    this function performs a mapping with the given sparse matrix,
    but re-weighted with an additional array, and applies it to the given input matrix
    Output is the mapping result

    Parameters
    ----------
    mapping : csr_matrix
        Un-weighted mapping from source to target
    xin : NDArray[float_]
        Input array subjected to the mapping
    rw : NDArray[float_]
        Re-weighting over the output elements (size should be size of xout = number of rows in the matrix) 

    Returns
    -------
    NDArray[float_]:
        the mapping result
    """

    afmc = diags(rw).dot(mapping)
    s = (np.ones(np.size(rw)) * afmc)
    s[s == 0] = 1.0E-13
    afmcc = afmc.dot(diags(1.0 / s))
    xout = np.array(afmcc * xin)
    return xout


def calc_correction_dfm2mf(
    mapping: csr_matrix, q_pre1: NDArray[float_], q_pre2: NDArray[float_], q_post2: NDArray[float_]
) -> NDArray[float_]:
    """
    this function computes the not-realized amounts in system1 
    by comparing demand and realization in system2 and applying the resulting
    fraction realized back on system1, which gives the not-realized values in system1 

    Parameters
    ----------
    mapping : csr_matrix
        Un-weighted mapping from system1 to system2
    q_pre1 : NDArray[float_]
        Input array of demand values in system1 
    q_pre2:  NDArray[float_]
        Input array of demand values in system2 
    q_post2:  NDArray[float_]
        realized values in system2

    Returns
    -------
    NDArray[float_]:
        the amounts in system1 that were NOT realized (i.o.w. correction terms)

    """
    alpha = np.maximum(0.0, (1. - q_post2 / np.maximum(q_pre2, 1.0E-13)))
    qcorr = np.array(alpha.dot(mapping.dot(diags(q_pre1))))
    return qcorr


def weight_from_flux_distribution(
    tgt_idx: NDArray[int_], src_idx: NDArray[int_], previous_flux: NDArray[float_]
) -> NDArray[float_]:
    """
    this function calculates the weight based on the flux distribution of a n:1 connection,
    so it can be used in the 1:n redistribution of an correction flux or volume.
    Input is the target and source index of the mapings sparse array, and previouse flux array at n
    Output is weight-array for inversed mapping

    Parameters
    ----------
    tgt_idx :NDArray[int_],
        target index of mapping sparse array
    src_idx :NDArray[int_],
        source index of mapping sparse array
    previous_flux : NDArray[float_]
        previous flux

    Returns
    -------
    NDArray[float_]:
        the weight based on the flux distribution of a n:1 connection,
        so it can be used in the 1:n redistribution of an correction flux or volume.
    """

    cnt = np.zeros(max(tgt_idx) + 1)
    weight = np.zeros(max(src_idx) + 1)
    for i in range(len(tgt_idx)):
        cnt[tgt_idx[i]] = cnt[tgt_idx[i]] + previous_flux[i]
    for i in range(len(tgt_idx)):
        weight[i] = previous_flux[i] / cnt[tgt_idx[i]]
    return weight


def get_dflow1d_lookup(
    dflow1d_file: Path,
) -> dict[tuple[float, float], int]:
    """
    read file with all uniek coupled dflow 1d and 2d nodes (represented by xy pairs). After initialisation
    of dflow, dict is filled with node-id's corresponding tot xy-pairs.
    this functions should be called after initialisation of dflow-fm.

    Parameters
    ----------
    workdir : Path
        directory where mapping input files can be found

    Returns
    -------
    tuple[dict[tuple[float, float], int], bool]
       The first value of the tupple is a dictionary of pairs of xy-coordinates to node numbers
       The second value is an indicator of whether the said dictionary could be filled without issues.
    """

    dflow1d_lookup = {}
    if dflow1d_file.is_file():
        dflow1d_data: NDArray[np.single] = np.loadtxt(
            dflow1d_file, dtype=np.single, ndmin=2, skiprows=0
        )
        dflow1d_x = dflow1d_data[:, 0]
        dflow1d_y = dflow1d_data[:, 1]
        # XMI/BMI call to dflow-fm with x and y list, returns id list with node numbers
        # dflowfm_MapCoordinateTo1DCellId(x, y, id)
        # for testing purpose, we take the id from the dat-file
        dflow1d_id = dflow1d_data[:, 2].astype(int) - 1
        nrpoints = dflow1d_data.shape[0]
        for i in range(nrpoints):
            if dflow1d_id[i] >= 0:
                dflow1d_lookup[(dflow1d_x[i], dflow1d_y[i])] = dflow1d_id[i]
            else:
                raise ValueError(
                    f"xy coordinate {dflow1d_x[i], dflow1d_y[i]} is not part of dflow's mesh"
                )
    else:
        raise ValueError(f"mapping file 'DFLOWFM1D_POINTS.DAT' was not found!")
    return dflow1d_lookup


def get_svat_lookup(workdir_msw: Path) -> dict[tuple[int, int], int]:
    """
    read file with all coupled MetaSWAP svat. Function creates a lookup, with the svat tuples (id, lay) as keys and the metaswap internal indexes as values

    Parameters
    ----------
    workdir_msw : Path
        directory where MetaSWAP mapping input files can be found

    Returns
    -------
    tuple[dict[tuple[int, int, int], bool]
       The first value of the tupple is a dictionary of pairs svat and layer to internal svat-number
       The second value is an indicator of whether the said dictionary could be filled without issues.
    """

    svat_lookup = {}
    msw_mod2svat_file = workdir_msw / "mod2svat.inp"
    if msw_mod2svat_file.is_file():
        svat_data: NDArray[np.int32] = np.loadtxt(
            msw_mod2svat_file, dtype=np.int32, ndmin=2
        )
        svat_id = svat_data[:, 1]
        svat_lay = svat_data[:, 2]
        for vi in range(svat_id.size):
            svat_lookup[(svat_id[vi], svat_lay[vi])] = vi
    else:
        raise ValueError(f"mapping file 'mod2svat.inp' was not found!")
    return svat_lookup


def get_dflow2d_lookup(workdir: Path) -> tuple[dict[tuple[float, float], int], bool]:
    """
    read file with all uniek coupled dflow 1d and 2d nodes (represented by xy pairs). After initialisation
    of dflow, dict is filled with node-id's corresponding tot xy-pairs.
    this functions should be called after initialisation of dflow-fm.

    Parameters
    ----------
    workdir : Path
        directory where mapping input files can be found

    Returns
    -------
    tuple[dict[tuple[float, float], int], bool]
       The first value of the tupple is a dictionary of pairs of xy-coordinates to node numbers
       The second value is an indicator of whether the said dictionary could be filled without issues.
    """

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
        id_ = np.array([0])  # dummy array, check 0-indexing
        ii = id_.shape[0]
        for i in range(ii):
            if id_[i] > 0:
                dflow2d_lookup[(dflow2d_x[i], dflow2d_y[i])] = id_[i]
            else:
                raise ValueError(
                    f"xy coordinate {dflow2d_x,dflow2d_y} is not part of dflow's mesh"
                )
    else:
        ok = False
    return dflow2d_lookup, ok
