import os
import subprocess
import textwrap
from collections.abc import Callable
from pathlib import Path

import pytest
import tomli
import tomli_w
from imod.mf6 import open_cbc, open_hds
from numpy.testing import assert_array_almost_equal
from primod.metamod import MetaMod
from pytest_cases import parametrize_with_cases

from tests.common_scripts.mf6_water_balance.combine import (
    create_modflow_waterbalance_file,
)
from tests.test_imod_coupler.test_utilities import numeric_csvfiles_equal


def mf6_output_files(path: Path) -> tuple[Path, Path, Path, Path]:
    """return paths to Modflow 6 output files"""
    path_mf6 = path / "Modflow6" / "GWF_1"

    return (
        path_mf6 / "GWF_1.hds",
        path_mf6 / "GWF_1.cbc",
        path_mf6 / "dis.dis.grb",
        path_mf6 / "GWF_1.lst",
    )


def msw_output_files(path: Path) -> Path:
    path_msw = path / "MetaSWAP"

    return path_msw / "msw" / "csv" / "tot_svat_per.csv"


def test_lookup_table_present(metaswap_lookup_table: Path) -> None:
    assert metaswap_lookup_table.is_dir()


def test_metaswap_dll_devel_present(modflow_dll_devel: Path) -> None:
    assert modflow_dll_devel.is_file()


def test_metaswap_dll_regression_present(modflow_dll_regression: Path) -> None:
    assert modflow_dll_regression.is_file()


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
    )

    for dependency in expected_dependencies:
        assert dependency in dep_dir_content


@parametrize_with_cases("metamod_model", prefix="fail_write_")
def test_metamod_write_failure(
    tmp_path_dev: Path,
    metamod_model: MetaMod,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
) -> None:
    """
    Test if iMOD Python throws a error during writing coupled models that
    shouldn't work.
    """

    # FUTURE: This might change to ValidationError
    with pytest.raises(ValueError):
        metamod_model.write(
            tmp_path_dev,
            modflow6_dll=modflow_dll_devel,
            metaswap_dll=metaswap_dll_devel,
            metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
        )


@parametrize_with_cases("metamod_model", prefix="fail_run_")
def test_metamod_run_failure(
    tmp_path_dev: Path,
    metamod_model: MetaMod,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
    run_coupler_function: Callable[[Path], None],
) -> None:
    """
    Test if coupled models run failed with the iMOD Coupler development version.
    """

    metamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
        modflow6_write_kwargs={"validate": False},  # Turn off validation
    )

    with pytest.raises(subprocess.CalledProcessError):
        run_coupler_function(tmp_path_dev / metamod_model._toml_name)


@parametrize_with_cases("metamod_model")
def test_metamod_develop(
    tmp_path_dev: Path,
    metamod_model: MetaMod,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
    run_coupler_function: Callable[[Path], None],
) -> None:
    """
    Test if coupled models run with the iMOD Coupler development version.
    """
    metamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )

    run_coupler_function(tmp_path_dev / metamod_model._toml_name)

    # Test if MetaSWAP output written
    assert len(list((tmp_path_dev / "MetaSWAP").glob("*/*.idf"))) == 1704

    # Test if Modflow6 output written
    headfile, cbcfile, _, _ = mf6_output_files(tmp_path_dev)

    assert headfile.exists()
    assert cbcfile.exists()
    # If computation failed, Modflow6 usually writes a headfile and cbcfile of 0
    # bytes.
    assert headfile.stat().st_size > 0
    assert cbcfile.stat().st_size > 0


@parametrize_with_cases("metamod_model")
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
    run_coupler_function: Callable[[Path], None],
    imod_coupler_exec_regression: Path,
) -> None:
    """
    Regression test if coupled models run with the iMOD Coupler development and
    regression version. Test if results are near equal.
    """

    metamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )

    run_coupler_function(tmp_path_dev / metamod_model._toml_name)

    # Read Modflow 6 output
    headfile_dev, cbcfile_dev, grbfile_dev, _ = mf6_output_files(tmp_path_dev)

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
    headfile_reg, cbcfile_reg, grbfile_reg, _ = mf6_output_files(tmp_path_reg)

    heads_reg = open_hds(headfile_reg, grbfile_reg)
    budgets_reg = open_cbc(cbcfile_reg, grbfile_reg)

    assert_array_almost_equal(heads_dev.compute(), heads_reg.compute(), decimal=8)

    assert budgets_dev.keys() == budgets_reg.keys()

    for varname in budgets_dev.keys():
        assert_array_almost_equal(
            budgets_dev[varname].compute(), budgets_reg[varname].compute(), decimal=8
        )


@pytest.mark.xfail(reason="MetaSWAP issues")
@parametrize_with_cases("metamod_model", glob="storage_coefficient_no_sprinkling")
def test_metamod_regression_balance_output(
    metamod_model: MetaMod,
    tmp_path_dev: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
    run_coupler_function: Callable[[Path], None],
    reference_result_folder: Path,
) -> None:
    """
    compares the numerical output of the devel build with the expected results
    """
    # Write model again, but now with paths to devel dll
    metamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )

    run_coupler_function(tmp_path_dev / metamod_model._toml_name)

    _, _, _, mf6_lst_file = mf6_output_files(tmp_path_dev)
    msw_balance_results = msw_output_files(tmp_path_dev)

    # create modflow balance csv
    mf6_balance_output_file = tmp_path_dev / "waterbalance_output.csv"
    create_modflow_waterbalance_file(
        mf6_lst_file,
        output_file_csv=mf6_balance_output_file,
    )

    # define tolerance for modflow and metamod csv files, per column.
    eps = 1e-4
    mf6_tolerance_balance: dict[str, tuple[float, float]] = {
        "default": (2 * eps, 2 * eps),
        "RCH:RCH_MSW_IN": (
            3 * eps,
            3 * eps,
        ),  # this illustrates how to set different tolerances per column
    }
    msw_tolerance_balance: dict[str, tuple[float, float]] = {
        "default": (2 * eps, 2 * eps),
    }

    assert numeric_csvfiles_equal(
        mf6_balance_output_file,
        reference_result_folder
        / "test_metamod_regression_no_sprinkling"
        / "waterbalance_output.csv",
        ";",
        mf6_tolerance_balance,
    )

    assert numeric_csvfiles_equal(
        msw_balance_results,
        reference_result_folder
        / "test_metamod_regression_no_sprinkling"
        / "tot_svat_per.csv",
        ",",
        msw_tolerance_balance,
    )


@parametrize_with_cases("metamod_ss,metamod_sc", prefix="cases_metamod_")
def test_metamodel_storage_options(
    metamod_ss: MetaMod,
    metamod_sc: MetaMod,
    tmp_path: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
    run_coupler_function: Callable[[Path], None],
) -> None:
    """
    Test and compare two coupled models with the Modflow 6 storage specified as
    storage coefficient and as specific storage. Test if results are near equal.
    """

    tmp_path_sc = tmp_path / "storage_coefficient"
    tmp_path_ss = tmp_path / "specific_storage"

    metamod_ss.write(
        tmp_path_ss,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )

    run_coupler_function(tmp_path_ss / metamod_ss._toml_name)

    # Read Modflow 6 output
    headfile_ss, cbcfile_ss, grbfile_ss, _ = mf6_output_files(tmp_path_ss)

    heads_ss = open_hds(headfile_ss, grbfile_ss)
    budgets_ss = open_cbc(cbcfile_ss, grbfile_ss)

    metamod_sc.write(
        tmp_path_sc,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )

    run_coupler_function(tmp_path_sc / metamod_sc._toml_name)

    # Read Modflow 6 output
    headfile_sc, cbcfile_sc, grbfile_sc, _ = mf6_output_files(tmp_path_sc)

    heads_sc = open_hds(headfile_sc, grbfile_sc)
    budgets_sc = open_cbc(cbcfile_sc, grbfile_sc)

    assert_array_almost_equal(heads_sc.compute(), heads_ss.compute(), decimal=8)

    assert budgets_sc.keys() == budgets_ss.keys()

    for varname in budgets_sc.keys():
        assert_array_almost_equal(
            budgets_sc[varname].compute(), budgets_ss[varname].compute(), decimal=8
        )


@parametrize_with_cases("metamod_model", glob="storage_coefficient_no_sprinkling")
def test_metamod_exchange_logging(
    tmp_path_dev: Path,
    metamod_model: MetaMod,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
    run_coupler_function: Callable[[Path], None],
) -> None:
    """
    Test if logging works as intended
    """
    metamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )
    add_logging_request_to_toml_file(tmp_path_dev, metamod_model._toml_name)

    run_coupler_function(tmp_path_dev / metamod_model._toml_name)

    # Test if logging netcdf's  were written
    assert len(list((tmp_path_dev).glob("*.nc"))) == 2


def add_logging_request_to_toml_file(toml_dir: Path, toml_filename: str) -> None:
    """
    This function takes as input the path to a toml file written by MetaMod. It then adds a reference to an
    output config file to it, and creates the same output config file.
    """

    # add reference to output_config to metamod's toml file
    with open(toml_dir / toml_filename, "rb") as f:
        toml_dict = tomli.load(f)

    with open(toml_dir / toml_filename, "wb") as f:
        toml_dict["driver"]["coupling"][0]["output_config_file"] = (
            "./output_config.toml"
        )
        tomli_w.dump(toml_dict, f)

    # write output_config file
    output_config_content = textwrap.dedent(
        """\
    [general]
    output_dir = "{workdir}"

    [exchanges.mf6_storage]
    type = "netcdf"

    [exchanges.msw_storage]
    type = "netcdf"
    """
    )
    path_quadruple_backslash = "\\\\".join(
        (str(toml_dir)).split("\\")
    )  # on print ,"\\\\" gets rendered as "\\"
    with open(toml_dir / "output_config.toml", "w") as f:
        f.write(output_config_content.format(workdir=path_quadruple_backslash))
