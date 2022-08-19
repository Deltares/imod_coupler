import operator
import os
from functools import reduce
from pathlib import Path
from typing import Any

import pydantic
import pytest
import tomli
import tomli_w
from imod.couplers.metamod import MetaMod
from imod.mf6 import Modflow6Simulation
from imod.msw import MetaSwapModel
from pytest_cases import fixture, parametrize, parametrize_with_cases

from imod_coupler.__main__ import run_coupler


def get_from_container(data_dict: dict[Any, Any], map_list: list[Any]) -> Any:
    """Gets the nested value of a container
    Adapted from https://stackoverflow.com/a/14692747/11038610"""
    return reduce(operator.getitem, map_list, data_dict)


def set_container(data_dict: dict[Any, Any], map_list: list[Any], value: Any) -> None:
    """Sets the nested value of a container
    Adapted from https://stackoverflow.com/a/14692747/11038610
    """
    get_from_container(data_dict, map_list[:-1])[map_list[-1]] = value


@pytest.fixture(scope="function")
def metamod_sprinkling(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:

    return MetaMod(
        prepared_msw_model,
        coupled_mf6_model,
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey="wells_msw",
    )


cases_missing_files = [
    ["driver", "kernels", "modflow6", "dll"],
    ["driver", "kernels", "metaswap", "dll"],
    ["driver", "coupling", 0, "mf6_msw_node_map"],
    ["driver", "coupling", 0, "mf6_msw_recharge_map"],
    ["driver", "coupling", 0, "mf6_msw_sprinkling_map"],
]


@pytest.mark.parametrize(
    "map_list",
    cases_missing_files,
)
def test_missing_files(
    metamod_sprinkling: MetaMod,
    map_list: list[Any],
    tmp_path: Path,
    modflow_dll_devel: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
) -> None:
    """This test assures that missing files result in an ValidationError"""

    metamod_sprinkling.write(
        tmp_path,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )

    config_path = tmp_path / metamod_sprinkling._toml_name

    with open(config_path, "rb") as f:
        config_dict = tomli.load(f)

    # Create temp file
    tmp_file = tmp_path / "tmp_file"
    tmp_file.touch()

    # Let the dict value point to the file
    set_container(config_dict, map_list, str(tmp_file))

    # Write the config file
    with open(config_path, "wb") as f:
        tomli_w.dump(config_dict, f)

    # Delete the tmp_file
    tmp_file.unlink()

    with pytest.raises(pydantic.ValidationError):
        run_coupler(config_path)


def test_sprinkling_requires_files(
    metamod_sprinkling: MetaMod,
    tmp_path: Path,
    modflow_dll_devel: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
) -> None:
    """This test assures that if sprinkling is activated,
    sprinkling files must be there as well.
    If not it must raise a ValueError."""

    metamod_sprinkling.write(
        tmp_path,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )

    config_path = tmp_path / metamod_sprinkling._toml_name

    with open(config_path, "rb") as f:
        config_dict = tomli.load(f)

    assert config_dict["driver"]["coupling"][0]["enable_sprinkling"]

    # Get the path of `mf6_msw_sprinkling_map`
    sprinkling_map = config_path.parent / get_from_container(
        config_dict, ["driver", "coupling", 0, "mf6_msw_sprinkling_map"]
    )
    # Delete `mf6_msw_sprinkling_map`

    sprinkling_map.unlink()

    with pytest.raises(pydantic.ValidationError):
        run_coupler(config_path)
