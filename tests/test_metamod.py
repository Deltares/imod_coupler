import os
import subprocess
from pathlib import Path

import pytest
from imod.couplers.metamod import MetaMod
from imod.mf6 import Modflow6Simulation, open_cbc, open_hds
from imod.msw import MetaSwapModel
from numpy.testing import assert_array_almost_equal
from pytest_cases import parametrize_with_cases


def case_metamod_model_sprinkling(
    coupled_mf6_model: Modflow6Simulation,
    msw_model: MetaSwapModel,
    metaswap_lookup_table: Path,
) -> MetaMod:

    # Override unsat_svat_path with path from environment
    msw_model.simulation_settings[
        "unsa_svat_path"
    ] = msw_model._render_unsaturated_database_path(metaswap_lookup_table)

    return MetaMod(
        msw_model,
        coupled_mf6_model,
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey="wells_msw",
    )


def case_metamod_model_no_sprinkling(
    coupled_mf6_model: Modflow6Simulation,
    msw_model: MetaSwapModel,
    metaswap_lookup_table: Path,
) -> MetaMod:

    # Override unsat_svat_path with path from environment
    msw_model.simulation_settings[
        "unsa_svat_path"
    ] = msw_model._render_unsaturated_database_path(metaswap_lookup_table)

    # Remove sprinkling package
    msw_model.pop("sprinkling")

    return MetaMod(
        msw_model,
        coupled_mf6_model,
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey=None,  # Do not couple to Modflow wel
    )


@pytest.fixture
def tmp_path_dev(
    tmp_path: Path,
) -> Path:
    return tmp_path / "develop"


@pytest.fixture
def tmp_path_reg(
    tmp_path: Path,
) -> Path:
    return tmp_path / "regression"


def read_log_for_success(logfile_path):
    with open(logfile_path, "r") as logfile:
        has_mf6_success_message = False
        has_msw_success_message = False
        for line in logfile:
            if "Normal termination of simulation." in line:
                has_mf6_success_message = True
            if "E N D   O F   M E T A S W A P" in line:
                has_msw_success_message = True

    return has_mf6_success_message, has_msw_success_message


def run_model(path: Path, imod_coupler_exec: Path):
    logfile_path = path / "metamod.log"
    with open(logfile_path, "w") as logfile:
        subprocess.run(
            [imod_coupler_exec, path / "imod_coupler.toml"],
            stdout=logfile,
            stderr=logfile,
        )


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


def test_modflow_dll_present(modflow_dll_devel: Path) -> None:
    assert modflow_dll_devel.is_file()


@parametrize_with_cases("metamod_model", cases=".")
def test_metamod_develop(
    tmp_path_dev: Path,
    metamod_model: MetaMod,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
    imod_coupler_exec_devel: Path,
):
    metamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )

    # Capture standard output and error in file (instead of StringIO) for
    # debugging purposes
    run_model(tmp_path_dev, imod_coupler_exec_devel)

    has_mf6_success_message, has_msw_success_message = read_log_for_success(
        tmp_path_dev / "metamod.log"
    )

    assert has_mf6_success_message
    assert has_msw_success_message

    # Test if MetaSWAP output written
    assert len(list((tmp_path_dev / "MetaSWAP").glob("*/*.idf"))) == 24

    # Test if Modflow6 output written
    headfile = tmp_path_dev / "Modflow6" / "GWF_1" / "GWF_1.hds"
    cbcfile = tmp_path_dev / "Modflow6" / "GWF_1" / "GWF_1.cbc"

    assert headfile.exists()
    assert cbcfile.exists()
    # If computation failed, Modflow6 usually writes a headfile and cbcfile of 0
    # bytes.
    assert headfile.stat().st_size > 0
    assert cbcfile.stat().st_size > 0


@parametrize_with_cases("metamod_model", cases=".")
def test_metamod_regression_sprinkling(
    metamod_model: MetaMod,
    tmp_path_dev: Path,
    tmp_path_reg: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
    metaswap_dll_regression: Path,
    metaswap_dll_dep_dir_regression: Path,
    modflow_dll_regression: Path,
    imod_coupler_exec_devel: Path,
    imod_coupler_exec_regression: Path,
):
    metamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )

    # Capture standard output and error in file (instead of StringIO) for
    # debugging purposes
    run_model(tmp_path_dev, imod_coupler_exec_devel)

    has_mf6_success_message, has_msw_success_message = read_log_for_success(
        tmp_path_dev / "metamod.log"
    )
    assert has_mf6_success_message
    assert has_msw_success_message

    # Read Modflow 6 output
    headfile_dev = tmp_path_dev / "Modflow6" / "GWF_1" / "GWF_1.hds"
    cbcfile_dev = tmp_path_dev / "Modflow6" / "GWF_1" / "GWF_1.cbc"
    grbfile_dev = tmp_path_dev / "Modflow6" / "GWF_1" / "dis.dis.grb"

    heads_dev = open_hds(headfile_dev, grbfile_dev)
    budgets_dev = open_cbc(cbcfile_dev, grbfile_dev)

    # Write model again, but now with paths to regression dll
    metamod_model.write(
        tmp_path_reg,
        modflow6_dll=modflow_dll_regression,
        metaswap_dll=metaswap_dll_regression,
        metaswap_dll_dependency=metaswap_dll_dep_dir_regression,
    )

    # Capture standard output and error in file (instead of StringIO) for
    # debugging purposes
    run_model(tmp_path_reg, imod_coupler_exec_regression)

    has_mf6_success_message, has_msw_success_message = read_log_for_success(
        tmp_path_reg / "metamod.log"
    )
    assert has_mf6_success_message
    assert has_msw_success_message

    # Read Modflow 6 output
    headfile_reg = tmp_path_reg / "Modflow6" / "GWF_1" / "GWF_1.hds"
    cbcfile_reg = tmp_path_reg / "Modflow6" / "GWF_1" / "GWF_1.cbc"
    grbfile_reg = tmp_path_reg / "Modflow6" / "GWF_1" / "dis.dis.grb"

    heads_reg = open_hds(headfile_reg, grbfile_reg)
    budgets_reg = open_cbc(cbcfile_reg, grbfile_reg)

    assert_array_almost_equal(heads_dev.compute(), heads_reg.compute(), decimal=8)

    assert budgets_dev.keys() == budgets_reg.keys()

    for varname in budgets_dev.keys():
        assert_array_almost_equal(budgets_dev[varname].compute(), budgets_reg[varname].compute(), decimal=8)
