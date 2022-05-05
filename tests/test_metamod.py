import os
from pathlib import Path

from imod.mf6 import Modflow6Simulation
from imod.msw import MetaSwapModel
from imod.couplers.metamod import MetaMod

import subprocess


def test_lookup_table_present(metaswap_lookup_table: Path) -> None:
    assert metaswap_lookup_table.is_dir()


def test_metaswap_dll_devel_present(modflow_dll_devel: Path) -> None:
    assert modflow_dll_devel.is_file()


def test_metaswap_dll_devel_present(modflow_dll_devel: Path) -> None:
    assert modflow_dll_devel.is_file()


def test_modflow_dll_devel_present(modflow_dll_devel: Path) -> None:
    assert modflow_dll_devel.is_file()


def test_modflow_dll_regression_present(modflow_dll_regression: Path) -> None:
    assert modflow_dll_regression.is_file()


def test_metaswap_dll_dep_dir_devel_contains_dependencies(
    metaswap_dll_dep_dir_devel: Path,
) -> None:
    dep_dir_content = os.listdir(metaswap_dll_dep_dir_devel)
    expected_dependencies = (
        "fmpich2.dll",
        "mpich2mpi.dll",
        "mpich2nemesis.dll",
        "TRANSOL.dll",
    )

    for dependency in expected_dependencies:
        assert dependency in dep_dir_content


def test_metaswap_dll_dep_dir_regression_contains_dependencies(
    metaswap_dll_dep_dir_regression: Path,
) -> None:
    dep_dir_content = os.listdir(metaswap_dll_dep_dir_regression)
    expected_dependencies = (
        "fmpich2.dll",
        "mpich2mpi.dll",
        "mpich2nemesis.dll",
        "TRANSOL.dll",
    )

    for dependency in expected_dependencies:
        assert dependency in dep_dir_content


def test_modflow_dll_present(modflow_dll: Path) -> None:
    assert modflow_dll.is_file()


def test_metamod_sprinkling(
    tmp_path: Path,
    coupled_mf6_model: Modflow6Simulation,
    msw_model: MetaSwapModel,
    metaswap_lookup_table: Path,
    metaswap_dll: Path,
    metaswap_dll_dep_dir: Path,
    modflow_dll: Path,
):
    # Override unsat_svat_path with path from .env
    msw_model.simulation_settings[
        "unsa_svat_path"
    ] = msw_model._render_unsaturated_database_path(metaswap_lookup_table)

    metamod = MetaMod(
        msw_model,
        coupled_mf6_model,
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey="wells_msw",
    )

    metamod.write(
        tmp_path,
        modflow6_dll=modflow_dll,
        metaswap_dll=metaswap_dll,
        metaswap_dll_dependency=metaswap_dll_dep_dir,
    )

    os.chdir(tmp_path)
    subprocess.run(["imodc", "metamod.toml"])

    assert len(list((tmp_path / "MetaSWAP").glob("*/*.idf"))) == 24
