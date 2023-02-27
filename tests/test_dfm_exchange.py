import numpy as np
import pytest

from imod_coupler.drivers.dfm_metamod.exchange import Exchange_balans

dflow_dim = 2
exchange_balans = Exchange_balans(dflow_dim)

# testdata
mf6_riv_active_positive = np.array([6, 6])
mf6_riv_active_negative = np.array([-4, 0])
mf6_riv_active = mf6_riv_active_positive + mf6_riv_active_negative
mf6_riv_passive = np.array([1, 2])
mf6_drn = np.array([1, 1])
msw_ponding = np.array([1, 0])
msw_sprinking = np.array([-1, -1])

ref_dict = {}
ref_dict["mf-riv2dflow1d_flux"] = mf6_riv_active
ref_dict["mf-riv2dflow1d_flux_positive"] = mf6_riv_active_positive
ref_dict["mf-riv2dflow1d_flux_negative"] = mf6_riv_active_negative
ref_dict["mf-riv2dflow1d_passive_flux"] = mf6_riv_passive
ref_dict["mf-drn2dflow1d_flux"] = mf6_drn
ref_dict["msw-ponding2dflow1d_flux"] = msw_ponding
ref_dict["msw-sprinkling2dflow1d_flux"] = msw_sprinking


def test_exchange_initialise() -> None:
    exchange_balans.initialise()
    for array in exchange_balans.demand.values():
        assert array.size == dflow_dim, "array dims are not as expected"
        assert np.max(array) == 0, "arrays is not initialised at 0"
    for array in exchange_balans.realised.values():
        assert array.size == dflow_dim, "array dims are not as expected"
        assert np.max(array) == 0, "arrays is not initialised at 0"


def test_exchange_set() -> None:
    # first initialise
    exchange_balans.initialise()
    # set arrays
    for i in range(3):
        exchange_balans.demand["mf-riv2dflow1d_flux"] = mf6_riv_active[:]
        exchange_balans.demand[
            "mf-riv2dflow1d_flux_positive"
        ] = mf6_riv_active_positive[:]
        exchange_balans.demand[
            "mf-riv2dflow1d_flux_negative"
        ] = mf6_riv_active_negative[:]
        exchange_balans.demand["mf-riv2dflow1d_passive_flux"] = mf6_riv_passive[:]
        exchange_balans.demand["mf-drn2dflow1d_flux"] = mf6_drn[:]
        exchange_balans.demand["msw-ponding2dflow1d_flux"] = msw_ponding[:]
        exchange_balans.demand["msw-sprinkling2dflow1d_flux"] = msw_sprinking[:]

        for label in exchange_balans.demand.keys():
            if label != "sum":
                np.testing.assert_array_equal(
                    exchange_balans.demand[label],
                    ref_dict[label],
                    err_msg="arrays is not set at right value",
                )


def test_exchange_sum() -> None:
    # first initialise
    exchange_balans.initialise()
    # set arrays
    exchange_balans.demand["mf-riv2dflow1d_flux"] = mf6_riv_active[:]
    exchange_balans.demand["mf-riv2dflow1d_flux_positive"] = mf6_riv_active_positive[:]
    exchange_balans.demand["mf-riv2dflow1d_flux_negative"] = mf6_riv_active_negative[:]
    exchange_balans.demand["mf-riv2dflow1d_passive_flux"] = mf6_riv_passive[:]
    exchange_balans.demand["mf-drn2dflow1d_flux"] = mf6_drn[:]
    exchange_balans.demand["msw-ponding2dflow1d_flux"] = msw_ponding[:]
    exchange_balans.demand["msw-sprinkling2dflow1d_flux"] = msw_sprinking[:]
    # test sum
    exchange_balans.sum_demand()
    np.testing.assert_array_equal(
        exchange_balans.demand["sum"],
        np.array([4.0, 8.0]),
        err_msg="computed sum of arrays is incorrect",
    )


def test_compute_realised() -> None:
    # first initialise
    exchange_balans.initialise()
    # set arrays
    exchange_balans.demand["mf-riv2dflow1d_flux"] = mf6_riv_active[:]
    exchange_balans.demand["mf-riv2dflow1d_flux_positive"] = mf6_riv_active_positive[:]
    exchange_balans.demand["mf-riv2dflow1d_flux_negative"] = mf6_riv_active_negative[:]
    exchange_balans.demand["mf-riv2dflow1d_passive_flux"] = mf6_riv_passive[:]
    exchange_balans.demand["mf-drn2dflow1d_flux"] = mf6_drn[:]
    exchange_balans.demand["msw-ponding2dflow1d_flux"] = msw_ponding[:]
    exchange_balans.demand["msw-sprinkling2dflow1d_flux"] = msw_sprinking[:]
    # sum demands
    exchange_balans.sum_demand()
    # set expected arrays
    dflow_realised = {
        0: np.array([3.6, 8.0]),
        1: np.array([3.0, 8.0]),
        2: np.array([1.0, 8.0]),
        3: np.array([0.0, 8.0]),
    }

    msw_expected_realised = {
        0: np.array([-0.6, -1.0]),
        1: np.array([0.0, -1.0]),
        2: np.array([0.0, -1.0]),
        3: np.array([0.0, -1.0]),
    }

    mf6_expected_realised = {
        0: np.array([-4.0, 0.0]),
        1: np.array([-4.0, 0.0]),
        2: np.array([-2.0, 0.0]),
        3: np.array([-1.0, 0.0]),
    }
    # test compute realised
    for i in range(4):
        exchange_balans.compute_realised(dflow_realised[i])
        np.testing.assert_array_almost_equal(
            exchange_balans.realised["dflow1d_flux2sprinkling_msw"],
            msw_expected_realised[i],
            err_msg="calculated msw realised sprinkling  != expected",
            decimal=3,
        )
        np.testing.assert_array_almost_equal(
            exchange_balans.realised["dflow1d_flux2mf-riv_negative"],
            mf6_expected_realised[i],
            err_msg="calculated mf6 realised negative riv1 != expected",
            decimal=3,
        )

    # final test for shortage larger than negative demands
    dflow_realised = np.array([-2, 8.0])
    with pytest.raises(ValueError):
        exchange_balans.compute_realised(dflow_realised)
