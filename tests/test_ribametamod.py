from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from imod.msw import MetaSwapModel
from primod.ribametamod import RibaMetaMod
from pytest_cases import parametrize_with_cases

from imod_coupler.drivers.ribametamod.exchange import ExchangeBalance

msw_outputlabel_ponding: str = "        Pssw(m3)"
msw_outputlabel_swsprinkling: str = "   ts2dfmput(m3)"


@pytest.mark.xdist_group(name="ribasim")
@parametrize_with_cases("ribametamod_model", glob="backwater_model")
def test_ribametamod_backwater(
    tmp_path_dev: Path,
    ribametamod_model: RibaMetaMod | MetaSwapModel,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    run_coupler_function: Callable[[Path], None],
    ribametamod_backwater_tot_svat_ref: Path,
) -> None:
    """
    Test if the backwater model works as expected
    """
    ribametamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        ribasim_dll=ribasim_dll_devel,
        ribasim_dll_dependency=ribasim_dll_dep_dir_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )
    run_coupler_function(tmp_path_dev / ribametamod_model._toml_name)
    tot_svat_reference = pd.read_csv(ribametamod_backwater_tot_svat_ref)
    tot_svat_test = pd.read_csv("metaswap/msw/csv/tot_svat_per.csv")
    assert tot_svat_test[msw_outputlabel_swsprinkling].equals(
        tot_svat_reference[msw_outputlabel_swsprinkling]
    )
    assert tot_svat_test[msw_outputlabel_ponding].equals(
        tot_svat_reference[msw_outputlabel_ponding]
    )


@pytest.mark.xdist_group(name="ribasim")
@parametrize_with_cases("ribametamod_model", glob="bucket_model")
def test_ribametamod_bucket(
    tmp_path_dev: Path,
    ribametamod_model: RibaMetaMod | MetaSwapModel,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    run_coupler_function: Callable[[Path], None],
    ribametamod_bucket_tot_svat_ref: Path,
) -> None:
    """
    Test if the bucket model works as expected
    """
    ribametamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        ribasim_dll=ribasim_dll_devel,
        ribasim_dll_dependency=ribasim_dll_dep_dir_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )
    run_coupler_function(tmp_path_dev / ribametamod_model._toml_name)
    tot_svat_reference = pd.read_csv(ribametamod_bucket_tot_svat_ref)
    tot_svat_test = pd.read_csv("metaswap/msw/csv/tot_svat_per.csv")
    assert tot_svat_test[msw_outputlabel_swsprinkling].equals(
        tot_svat_reference[msw_outputlabel_swsprinkling]
    )
    assert tot_svat_test[msw_outputlabel_ponding].equals(
        tot_svat_reference[msw_outputlabel_ponding]
    )


@pytest.mark.xdist_group(name="ribasim")
@parametrize_with_cases("ribametamod_model", glob="two_basin_model")
def test_ribametamod_two_basin(
    tmp_path_dev: Path,
    ribametamod_model: RibaMetaMod,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    run_coupler_function: Callable[[Path], None],
    ribametamod_two_basin_tot_svat_ref: Path,
) -> None:
    """
    Test if the two-basin model model works as expected
    """
    ribametamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        ribasim_dll=ribasim_dll_devel,
        ribasim_dll_dependency=ribasim_dll_dep_dir_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )

    run_coupler_function(tmp_path_dev / ribametamod_model._toml_name)
    tot_svat_reference = pd.read_csv(ribametamod_two_basin_tot_svat_ref)
    tot_svat_test = pd.read_csv("metaswap/msw/csv/tot_svat_per.csv")
    assert tot_svat_test[msw_outputlabel_swsprinkling].equals(
        tot_svat_reference[msw_outputlabel_swsprinkling]
    )
    assert tot_svat_test[msw_outputlabel_ponding].equals(
        tot_svat_reference[msw_outputlabel_ponding]
    )


@pytest.mark.xdist_group(name="ribasim")
@parametrize_with_cases("ribametamod_model", glob="two_basin_model_users")
def test_ribametamod_two_basin_users(
    tmp_path_dev: Path,
    ribametamod_model: RibaMetaMod,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    run_coupler_function: Callable[[Path], None],
    ribametamod_two_basin_tot_svat_ref: Path,
) -> None:
    """
    Test if the two-basin model model works as expected
    """
    ribametamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        ribasim_dll=ribasim_dll_devel,
        ribasim_dll_dependency=ribasim_dll_dep_dir_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )

    run_coupler_function(tmp_path_dev / ribametamod_model._toml_name)
    tot_svat_reference = pd.read_csv(ribametamod_two_basin_tot_svat_ref)
    tot_svat_test = pd.read_csv("metaswap/msw/csv/tot_svat_per.csv")
    assert tot_svat_test[msw_outputlabel_swsprinkling].equals(
        tot_svat_reference[msw_outputlabel_swsprinkling]
    )
    assert tot_svat_test[msw_outputlabel_ponding].equals(
        tot_svat_reference[msw_outputlabel_ponding]
    )


@pytest.mark.xdist_group(name="ribasim")
@parametrize_with_cases("ribametamod_model", glob="two_basin_model")
def test_ribametamod_two_basin(
    tmp_path_dev: Path,
    ribametamod_model: RibaMetaMod,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    run_coupler_function: Callable[[Path], None],
    ribametamod_two_basin_tot_svat_ref: Path,
) -> None:
    """
    Test if the two-basin model model works as expected
    """
    ribametamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        ribasim_dll=ribasim_dll_devel,
        ribasim_dll_dependency=ribasim_dll_dep_dir_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )

    run_coupler_function(tmp_path_dev / ribametamod_model._toml_name)
    tot_svat_reference = pd.read_csv(ribametamod_two_basin_tot_svat_ref)
    tot_svat_test = pd.read_csv("metaswap/msw/csv/tot_svat_per.csv")
    assert tot_svat_test[msw_outputlabel_swsprinkling].equals(
        tot_svat_reference[msw_outputlabel_swsprinkling]
    )
    assert tot_svat_test[msw_outputlabel_ponding].equals(
        tot_svat_reference[msw_outputlabel_ponding]
    )


def test_exchange_balance() -> None:
    shape = 4
    labels = ["flux-1", "flux-2"]
    exchange = ExchangeBalance(shape=shape, labels=labels)

    # exchange demands to class
    array_negative = np.zeros(shape=shape, dtype=np.float64)
    array_positive = np.zeros(shape=shape, dtype=np.float64)

    # seperate negative contributions for n:1 exchange
    array_negative[0] = -10
    array_negative[1] = -10
    array_positive[0] = 0.0
    array_positive[1] = 5.0

    demand_array = array_negative + array_positive
    exchange.demands["flux-1"] = demand_array
    exchange.demands["flux-2"] = demand_array * 0.5
    exchange.demands_negative["flux-1"] = array_negative
    exchange.demands_negative["flux-2"] = array_negative * 0.5

    # check summed demand
    assert np.all(exchange.demand == demand_array + (demand_array * 0.5))
    # check summed negative demand
    assert np.all(exchange.demand_negative == array_negative + (array_negative * 0.5))

    # evaluate realised method
    realised = np.zeros(shape=shape, dtype=np.float64)
    realised[0] = -5.0
    realised[1] = -5.0
    # compute
    exchange.compute_realised(realised)
    # compare: realised_factor = 1 - (-shortage - sum_negative_demands)
    realised_factor = np.zeros(shape=shape, dtype=np.float64)
    realised_factor[0] = 1 - (-10 / -15)
    realised_factor[1] = 1 - (-2.5 / -15)

    expected_flux1 = np.zeros(shape=shape, dtype=np.float64)
    expected_flux2 = np.zeros(shape=shape, dtype=np.float64)
    expected_flux1[0] = realised_factor[0] * array_negative[0]
    expected_flux2[0] = realised_factor[0] * array_negative[0] * 0.5
    expected_flux1[1] = realised_factor[1] * array_negative[1]
    expected_flux2[1] = realised_factor[1] * array_negative[1] * 0.5
    assert np.all(expected_flux1 == exchange.realised_negative["flux-1"])
    assert np.all(expected_flux2 == exchange.realised_negative["flux-2"])

    compute_realised = np.zeros(shape=shape, dtype=np.float64)
    compute_realised[0] = (
        exchange.realised_negative["flux-1"][0]
        + exchange.realised_negative["flux-2"][0]
        + array_positive[0]
        + (array_positive[0] * 0.5)
    )
    compute_realised[1] = (
        exchange.realised_negative["flux-1"][1]
        + exchange.realised_negative["flux-2"][1]
        + array_positive[1]
        + (array_positive[1] * 0.5)
    )
    assert np.all(np.isclose(realised, compute_realised))

    # check if reset zeros arrays
    exchange.reset()
    assert np.all(exchange.demand == np.zeros(shape=shape, dtype=np.float64))
    assert np.all(exchange.demand_negative == np.zeros(shape=shape, dtype=np.float64))

    # check if errors are thrown
    # shortage larger than negative demands
    shape = 1
    labels = ["flux-1"]
    exchange = ExchangeBalance(shape=shape, labels=labels)
    exchange.demands["flux-1"] = np.ones(shape=shape, dtype=np.float64) * -4
    exchange.demands_negative["flux-1"] = np.ones(shape=shape, dtype=np.float64) * -4
    realised = np.ones(shape=shape, dtype=np.float64) * 2
    with pytest.raises(
        ValueError,
        match="Invalid realised values: found shortage larger than negative demand contributions",
    ):
        exchange.compute_realised(realised)

    # shortage for positive demand
    shape = 1
    labels = ["flux-1"]
    exchange = ExchangeBalance(shape=shape, labels=labels)
    exchange.demands["flux-1"] = np.ones(shape=shape, dtype=np.float64) * 10
    exchange.demands_negative["flux-1"] = np.ones(shape=shape, dtype=np.float64) * -4
    realised = np.ones(shape=shape, dtype=np.float64) * 8
    with pytest.raises(
        ValueError, match="Invalid realised values: found shortage for positive demand"
    ):
        exchange.compute_realised(realised)
