import os
import subprocess
from pathlib import Path
from typing import Tuple

import pytest
from imod.couplers.metamod import MetaMod
from imod.mf6 import open_cbc, open_hds
from numpy.testing import assert_array_almost_equal
from pytest_cases import parametrize_with_cases


def mf6_output_files(path: Path) -> Tuple[Path, Path, Path]:
    """return paths to Modflow 6 output files"""
    path_mf6 = path / "Modflow6" / "GWF_1"

    return path_mf6 / "GWF_1.hds", path_mf6 / "GWF_1.cbc", path_mf6 / "dis.dis.grb"


def test_lookup_table_present(metaswap_lookup_table: Path) -> None:
    assert metaswap_lookup_table.is_dir()


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
    imod_coupler_exec_devel: Path,
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
        subprocess.run(
            [imod_coupler_exec_devel, tmp_path_dev / metamod_model._toml_name],
            check=True,
        )


@parametrize_with_cases("metamod_model", prefix="case_")
def test_metamod_develop(
    tmp_path_dev: Path,
    metamod_model: MetaMod,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
    imod_coupler_exec_devel: Path,
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

    subprocess.run(
        [imod_coupler_exec_devel, tmp_path_dev / metamod_model._toml_name], check=True
    )

    # Test if MetaSWAP output written
    assert len(list((tmp_path_dev / "MetaSWAP").glob("*/*.idf"))) == 1704

    # Test if Modflow6 output written
    headfile, cbcfile, _ = mf6_output_files(tmp_path_dev)

    assert headfile.exists()
    assert cbcfile.exists()
    # If computation failed, Modflow6 usually writes a headfile and cbcfile of 0
    # bytes.
    assert headfile.stat().st_size > 0
    assert cbcfile.stat().st_size > 0


@parametrize_with_cases("metamod_model", prefix="case_")
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

    subprocess.run(
        [imod_coupler_exec_devel, tmp_path_dev / metamod_model._toml_name], check=True
    )

    # Read Modflow 6 output
    headfile_dev, cbcfile_dev, grbfile_dev = mf6_output_files(tmp_path_dev)

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
    headfile_reg, cbcfile_reg, grbfile_reg = mf6_output_files(tmp_path_reg)

    heads_reg = open_hds(headfile_reg, grbfile_reg)
    budgets_reg = open_cbc(cbcfile_reg, grbfile_reg)

    assert_array_almost_equal(heads_dev.compute(), heads_reg.compute(), decimal=8)

    assert budgets_dev.keys() == budgets_reg.keys()

    for varname in budgets_dev.keys():
        assert_array_almost_equal(
            budgets_dev[varname].compute(), budgets_reg[varname].compute(), decimal=8
        )


@parametrize_with_cases("metamod_ss,metamod_sc", prefix="cases_")
def test_metamodel_storage_options(
    metamod_ss: MetaMod,
    metamod_sc: MetaMod,
    tmp_path: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
    imod_coupler_exec_devel: Path,
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

    subprocess.run(
        [imod_coupler_exec_devel, tmp_path_ss / metamod_ss._toml_name], check=True
    )

    # Read Modflow 6 output
    headfile_ss, cbcfile_ss, grbfile_ss = mf6_output_files(tmp_path_ss)

    heads_ss = open_hds(headfile_ss, grbfile_ss)
    budgets_ss = open_cbc(cbcfile_ss, grbfile_ss)

    metamod_sc.write(
        tmp_path_sc,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )

    subprocess.run(
        [imod_coupler_exec_devel, tmp_path_sc / metamod_sc._toml_name], check=True
    )

    # Read Modflow 6 output
    headfile_sc, cbcfile_sc, grbfile_sc = mf6_output_files(tmp_path_sc)

    heads_sc = open_hds(headfile_sc, grbfile_sc)
    budgets_sc = open_cbc(cbcfile_sc, grbfile_sc)

    assert_array_almost_equal(heads_sc.compute(), heads_ss.compute(), decimal=8)

    assert budgets_sc.keys() == budgets_ss.keys()

    for varname in budgets_sc.keys():
        assert_array_almost_equal(
            budgets_sc[varname].compute(), budgets_ss[varname].compute(), decimal=8
        )
