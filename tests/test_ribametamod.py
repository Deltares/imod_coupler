from collections.abc import Callable
from pathlib import Path

import pandas as pd
import pytest
from imod.msw import MetaSwapModel
from primod.ribametamod import RibaMetaMod
from pytest_cases import parametrize_with_cases


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
    bucket_ribametamod_sprinkling_tot_svat_ref: Path,
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
    tot_svat_reference = pd.read_csv(bucket_ribametamod_sprinkling_tot_svat_ref)
    tot_svat_test = pd.read_csv("metaswap/msw/csv/tot_svat_per.csv")
    assert tot_svat_test["        Pssw(m3)"].equals(
        tot_svat_reference["        Pssw(m3)"]
    )
    assert tot_svat_test["   ts2dfmput(m3)"].equals(
        tot_svat_reference["   ts2dfmput(m3)"]
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
    two_basin_ribametamod_tot_svat_ref: Path,
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
    tot_svat_reference = pd.read_csv(two_basin_ribametamod_tot_svat_ref)
    tot_svat_test = pd.read_csv("metaswap/msw/csv/tot_svat_per.csv")
    assert tot_svat_test["        Pssw(m3)"].equals(
        tot_svat_reference["        Pssw(m3)"]
    )
    assert tot_svat_test["   ts2dfmput(m3)"].equals(
        tot_svat_reference["   ts2dfmput(m3)"]
    )
