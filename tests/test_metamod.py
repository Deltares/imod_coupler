import os
from pathlib import Path


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
