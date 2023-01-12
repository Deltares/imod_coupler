#%%
from math import isclose
from pathlib import Path

import numpy as np
from numpy import float_
from numpy.typing import NDArray

from imod_coupler.drivers.dfm_metamod.mapping_functions import (
    calc_correction,
    get_dflow1d_lookup,
    mapping_active_mf_dflow1d,
    weight_from_flux_distribution,
)
from imod_coupler.utils import Operator, create_mapping


def test_mappers_general(
    dflow1d_mapping_file,
    mapping_file_mf6_river_to_dfm_1d_q,
    mapping_file_dfm_1d_waterlevel_to_mf6_river_stage,
) -> None:

    # Test exchange MF-DFLOW1D
    # create dummy arrays to exchange

    # mf riv1-flux to exchange
    mf_riv1_flux = np.array([3, 3, 4, 4, 4])
    # dflow1d flux and stage to exchange
    dflow1d_flux = np.array([6, 7, 8])
    dflow1d_stage = np.array([4, 5, 6])

    # get dflow-id based on xy-coordinates after initialisation (now as test from file)
    dflow1d_lookup = get_dflow1d_lookup(dflow1d_mapping_file)

    # create mapping for mf-dflow1d
    # there is no previous flux geven for weight distributed weights,
    # so DFLOW 1D stage -> MF RIV 1 exchange is not availble at this time
    map_active_mod_dflow1d, mask_active_mod_dflow1d = mapping_active_mf_dflow1d(
        mapping_file_mf6_river_to_dfm_1d_q,
        mapping_file_dfm_1d_waterlevel_to_mf6_river_stage,
        dflow1d_lookup,
    )

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
    np.testing.assert_allclose(
        mf_riv1_stage_receive_expected,
        mf_riv1_stage_receive,
        rtol=0.001,
        atol=0.0,
    )

    # MF RIV 1 -> DFLOW 1D flux
    # flux is always n:1, so values are summed
    dflow1d_flux_receive_expected = np.array([3 + 3, 4, 4 + 4])
    dflow1d_flux_receive = np.array([0, 0, 0])
    dflow1d_flux_receive = (
        mask_active_mod_dflow1d["mf-riv2dflow1d_flux"][:] * dflow1d_flux_receive[:]
        + map_active_mod_dflow1d["mf-riv2dflow1d_flux"].dot(mf_riv1_flux)[:]
    )
    np.testing.assert_allclose(
        dflow1d_flux_receive_expected, dflow1d_flux_receive, rtol=0.001, atol=0.0
    )

    # DFLOW 1D flux -> MF RIV 1 flux
    # flux is always 1:n, decomposition based on previous Mf -> DFLOW flux distribution

    # create new mapping based on  previous MF -> dflow flux exchange distribution
    # for now, all mappingfiles are read in again, this could be optimised in the future
    map_active_mod_dflow1d, mask_active_mod_dflow1d = mapping_active_mf_dflow1d(
        mapping_file_mf6_river_to_dfm_1d_q,
        mapping_file_dfm_1d_waterlevel_to_mf6_river_stage,
        dflow1d_lookup,
        mf_riv1_flux,
    )
    # expected results
    weights = np.array([3 / 6, 3 / 6, 1, 4 / 8, 4 / 8])
    mf_riv1_flux_receive_expected = np.array(
        [6 * weights[0], 6 * weights[1], 7 * weights[2], 8 * weights[3], 8 * weights[0]]
    )
    mf_riv1_flux_receive = np.array([0, 0, 0, 0, 0])
    mf_riv1_flux_receive = (
        mask_active_mod_dflow1d["dflow1d2mf-riv_flux"][:] * mf_riv1_flux_receive[:]
        + map_active_mod_dflow1d["dflow1d2mf-riv_flux"].dot(dflow1d_flux)[:]
    )
    np.testing.assert_allclose(
        mf_riv1_flux_receive_expected, mf_riv1_flux_receive, rtol=0.001, atol=0.0
    )


def test_correction_from_flux_distribution() -> None:
    # test calculated correction based on weights from first flux estimate
    # uses the weights to construct the weighted mapping from the dfm-mf6 mapping table
    # and applies the mapping table to calculate the corrections in terms of mf6 fluxes
    # mf-riv1 elements=5
    # dfow1d  elements=3

    # set dummy variables
    dfm_index = np.array([0, 0, 1, 1, 2])
    mf6_index = np.array([0, 1, 2, 3, 4])
    mf6_demand = np.array([1, 2, 3, 4, 5])
    # forward mapping
    map_mf2dfm, mask_mf2dfm = create_mapping(
        mf6_index, dfm_index, max(mf6_index) + 1, max(dfm_index) + 1, Operator.SUM
    )
    # Apply new mapping to mf6 fluxes to get the demand flux on the dfm side
    dfm_demand = map_mf2dfm.dot(mf6_demand)
    # produce the realized fluxes on the dfm side, calculate the corrections.
    dfm_realized = (0.5, 1.0, 0.7) * dfm_demand
    # calculate the correction fluxes
    dfm_corr = np.maximum(dfm_demand - dfm_realized, 0.0)
    # create reverse mapping, but with the mf6 demands as weights
    calculated_weight = weight_from_flux_distribution(dfm_index, mf6_index, mf6_demand)

    # evaluate weight distribution
    expected_weight = np.array([1 / 3, 2 / 3, 3 / 7, 4 / 7, 1])
    np.testing.assert_almost_equal(expected_weight, calculated_weight)

    map_dfm2mf, mask_dfm2mf = create_mapping(
        dfm_index,
        mf6_index,
        max(dfm_index) + 1,
        max(mf6_index) + 1,
        Operator.WEIGHT,
        calculated_weight,
    )
    # apply the weighted mapping to the correction values
    calculated_corr = map_dfm2mf.dot(dfm_corr)

    # evaluate calculated correction array in mf
    expected_corr = np.array([0.5, 1.0, 0.0, 0.0, 1.5])
    np.testing.assert_almost_equal(expected_corr, calculated_corr)


def test_calc_correction() -> None:
    # test calculation of proportional correction between estimated and realized values
    # mf-riv1 elements=5
    # dfow1d  elements=3

    # set dummy variables
    dfm_index = np.array([0, 0, 1, 1, 2])
    mf6_index = np.array([0, 1, 2, 3, 4])
    mf6_demand = np.array([1, 2, 3, 4, 5])

    # forward mapping
    map_mf2dfm, mask_mf2dfm = create_mapping(
        mf6_index, dfm_index, max(mf6_index) + 1, max(dfm_index) + 1, Operator.SUM
    )

    # Apply new mapping to mf6 fluxes to get the demand flux on the dfm side
    dfm_demand = map_mf2dfm.dot(mf6_demand)
    # produce the realized fluxes on the dfm side, calculate the corrections.
    dfm_realized = (0.5, 1.0, 0.7) * dfm_demand

    calculated_corr = calc_correction(map_mf2dfm, mf6_demand, dfm_demand, dfm_realized)

    # evaluate calculated correction array in mf
    expected_corr = np.array([0.5, 1.0, 0.0, 0.0, 1.5])
    np.testing.assert_almost_equal(expected_corr, calculated_corr)
