import os
import subprocess
from pathlib import Path

import pytest
from imod.couplers.metamod import MetaMod
from imod.mf6 import Modflow6Simulation, open_cbc, open_hds, StorageCoefficient
from imod.msw import MetaSwapModel
from numpy.testing import assert_array_almost_equal
from pytest_cases import parametrize_with_cases, parametrize, fixture


@fixture(scope="function")
def prepared_msw_model(
    msw_model: MetaSwapModel,
    metaswap_lookup_table: Path,
) -> MetaSwapModel:
    # Override unsat_svat_path with path from environment
    msw_model.simulation_settings[
        "unsa_svat_path"
    ] = msw_model._render_unsaturated_database_path(metaswap_lookup_table)

    return msw_model


@parametrize("use_sprinkling", [True, False])
def case_metamod_sprinkling(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
    use_sprinkling: bool,
) -> MetaMod:

    if not use_sprinkling:
        prepared_msw_model.pop("sprinkling")
        mf6_wel_pkgkey = None
    else:
        mf6_wel_pkgkey = "wells_msw"

    return MetaMod(
        prepared_msw_model,
        coupled_mf6_model,
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey=mf6_wel_pkgkey,
    )


def case_metamod_storage_coefficient(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:

    gwf_model = coupled_mf6_model["GWF_1"]

    # Specific storage package
    # gwf_model["sto"] = mf6.SpecificStorage(1e-3, 0.1, True, 0)
    sto_ds = gwf_model.pop("sto").dataset

    # Confined: S = Ss * b
    # Where 'S' is storage coefficient, 'Ss' specific
    # storage, and 'b' thickness.
    # https://en.wikipedia.org/wiki/Specific_storage

    dis_ds = gwf_model["dis"].dataset
    top = dis_ds["bottom"].shift(layer=1)
    top[0] = dis_ds["top"]
    b = top - dis_ds["bottom"]

    sto_ds["storage_coefficient"] = sto_ds["specific_storage"] * b
    sto_ds = sto_ds.drop_vars("specific_storage")

    gwf_model["sto"] = StorageCoefficient(**sto_ds)
    # reassign gwf model
    coupled_mf6_model["GWF_1"] = gwf_model

    return MetaMod(
        prepared_msw_model,
        coupled_mf6_model,
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey="wells_msw",
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


@parametrize_with_cases("metamod_model", cases=".", prefix="case_metamod_")
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

    subprocess.run(
        [imod_coupler_exec_devel, tmp_path_dev / metamod_model._toml_name], check=True
    )

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


@parametrize_with_cases("metamod_model", cases=".", prefix="case_metamod_")
def test_metamod_regression(
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

    subprocess.run(
        [imod_coupler_exec_devel, tmp_path_dev / metamod_model._toml_name], check=True
    )

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

    subprocess.run(
        [imod_coupler_exec_regression, tmp_path_reg / metamod_model._toml_name],
        check=True,
    )

    # Read Modflow 6 output
    headfile_reg = tmp_path_reg / "Modflow6" / "GWF_1" / "GWF_1.hds"
    cbcfile_reg = tmp_path_reg / "Modflow6" / "GWF_1" / "GWF_1.cbc"
    grbfile_reg = tmp_path_reg / "Modflow6" / "GWF_1" / "dis.dis.grb"

    heads_reg = open_hds(headfile_reg, grbfile_reg)
    budgets_reg = open_cbc(cbcfile_reg, grbfile_reg)

    assert_array_almost_equal(heads_dev.compute(), heads_reg.compute(), decimal=8)

    assert budgets_dev.keys() == budgets_reg.keys()

    for varname in budgets_dev.keys():
        assert_array_almost_equal(
            budgets_dev[varname].compute(), budgets_reg[varname].compute(), decimal=8
        )
