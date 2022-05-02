import os
from pathlib import Path


def test_lookup_table_present(metaswap_lookup_table: Path) -> None:
    assert metaswap_lookup_table.is_dir()


def test_metaswap_dll_present(metaswap_dll: Path) -> None:
    assert metaswap_dll.is_file()


def test_metaswap_dll_dep_dir_contains_dependencies(metaswap_dll_dep_dir: Path) -> None:
    dep_dir_content = os.listdir(metaswap_dll_dep_dir)
    expected_dependencies = (
        "fmpich2.dll",
        "mpich2mpi.dll",
        "mpich2nemesis.dll",
        "TRANSOL.dll",
    )

    for dependency in expected_dependencies:
        assert (
            dependency in dep_dir_content
        ), f"{dependency} is not in metaswap_dll_dep_dir."


def test_modflow_dll_present(modflow_dll: Path) -> None:
    assert modflow_dll.is_file()
