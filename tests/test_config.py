import os
from pathlib import Path

import pydantic
import pytest
import tomli
from imod.couplers.metamod import MetaMod
from imod.mf6 import Modflow6Simulation
from imod.msw import MetaSwapModel
from pytest_cases import fixture, parametrize, parametrize_with_cases

from imod_coupler.__main__ import run_coupler


def case_sprinkling(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:

    return MetaMod(
        prepared_msw_model,
        coupled_mf6_model,
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey="wells_msw",
    )


@parametrize_with_cases("metamod_model", cases=".", prefix="case_")
def test_missing_files(
    metamod_model: MetaMod,
    tmp_path: Path,
    modflow_dll_devel: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
):
    metamod_model.write(
        tmp_path,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )

    config_path = tmp_path / metamod_model._toml_name

    with open(config_path, "rb") as f:
        config_dict = tomli.load(f)

    os.chdir(tmp_path)
    Path(config_dict["driver"]["coupling"][0]["mf6_msw_node_map"]).unlink()

    with pytest.raises(pydantic.ValidationError):
        run_coupler(config_path)
