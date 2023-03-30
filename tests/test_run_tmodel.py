import shutil
import subprocess
from pathlib import Path

import pytest
from fixtures.fixture_model import (
    remove_exchange_file_references,
    run_waterbalance_script_on_tmodel,
    set_toml_file_tmodel,
    set_workdir_in_logging_config_file,
)
from test_scripts.water_balance.combine import create_waterbalance_file
from test_utilities import (
    fill_para_sim_template,
    numeric_csvfiles_equal,
    tolerance_balance,
)

from imod_coupler.__main__ import run_coupler

sep = ";"


def test_run_tmodel_no_sprinkling(
    tmp_path_dev: Path,
    tmodel_input_folder: Path,
    modflow_dll_devel: Path,
    dflowfm_dll: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    metaswap_lookup_table: Path,
    reference_result_folder: Path,
    imod_coupler_exec_devel: Path,
) -> None:
    shutil.copytree(tmodel_input_folder, tmp_path_dev)

    toml_file_path = tmp_path_dev / "imod_coupler.toml"
    output_config_path = tmp_path_dev / "output_config.toml"

    set_toml_file_tmodel(
        toml_file_path,
        modflow_dll_devel,
        metaswap_dll_devel,
        metaswap_dll_dep_dir_devel,
        dflowfm_dll,
    )

    files_to_skip = {
        "mf6_msw_sprinkling_map",
        "mf6_msw_well_pkg",
    }
    remove_exchange_file_references(toml_file_path, files_to_skip)

    set_workdir_in_logging_config_file(output_config_path, tmp_path_dev)
    fill_para_sim_template(tmp_path_dev / "MetaSWAP", metaswap_lookup_table)

    subprocess.run(
        [str(imod_coupler_exec_devel), toml_file_path],
        check=True,
    )

    waterbalance_result = run_waterbalance_script_on_tmodel(
        tmp_path_dev, "T-MODEL-F.LST"
    )

    csv_reference_file = (
        reference_result_folder / "test_run_tmodel" / "waterbalance.csv"
    )

    numeric_csvfiles_equal(
        waterbalance_result,
        csv_reference_file,
        sep,
        tolerance_balance,
    )


def test_run_tmodel_f_no_sprinkling(
    tmp_path_dev: Path,
    tmodel_f_input_folder: Path,
    modflow_dll_devel: Path,
    dflowfm_dll: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    metaswap_lookup_table: Path,
    reference_result_folder: Path,
    imod_coupler_exec_devel: Path,
) -> None:
    shutil.copytree(tmodel_f_input_folder, tmp_path_dev)
    toml_file_path = tmp_path_dev / "imod_coupler.toml"
    output_config_path = tmp_path_dev / "output_config.toml"

    set_toml_file_tmodel(
        toml_file_path,
        modflow_dll_devel,
        metaswap_dll_devel,
        metaswap_dll_dep_dir_devel,
        dflowfm_dll,
    )

    files_to_skip = {
        "mf6_msw_sprinkling_map",
        "mf6_msw_well_pkg",
    }
    remove_exchange_file_references(toml_file_path, files_to_skip)
    set_workdir_in_logging_config_file(output_config_path, tmp_path_dev)
    fill_para_sim_template(tmp_path_dev / "MetaSWAP", metaswap_lookup_table)
    subprocess.run(
        [str(imod_coupler_exec_devel), toml_file_path],
        check=True,

    waterbalance_result = run_waterbalance_script_on_tmodel(
        tmp_path_dev, "T-MODEL-F.LST"
    )

    csv_reference_file = (
        reference_result_folder / "test_run_tmodel" / "waterbalance.csv"
    )

    assert numeric_csvfiles_equal(
        waterbalance_result, csv_reference_file, ";", tolerance_balance
    )


@pytest.mark.maintenance
def test_run_tmodel_f_with_metamod(
    tmp_path_dev: Path,
    tmodel_f_input_folder: Path,
    modflow_dll_devel: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    metaswap_lookup_table: Path,
    reference_result_folder: Path,
    imod_coupler_exec_devel: Path,
) -> None:
    """
    this test runs t_model_f with the metamod driver (so without dflow)
    It can be used to compare the test results of the metamod simulation with the dfm_metamod simulation in which we disable
    all the dfm-related couplings.
    """
    shutil.copytree(tmodel_f_input_folder, tmp_path_dev)
    toml_file_path = tmp_path_dev / "metamod.toml"

    set_toml_file_tmodel(
        toml_file_path,
        modflow_dll_devel,
        metaswap_dll_devel,
        metaswap_dll_dep_dir_devel,
    )

    fill_para_sim_template(tmp_path_dev / "MetaSWAP", metaswap_lookup_table)

    subprocess.run(
        [str(imod_coupler_exec_devel), toml_file_path],
        check=True,
    )


def test_run_tmodel_f_without_dflow(
    tmp_path_dev: Path,
    tmodel_f_input_folder: Path,
    modflow_dll_devel: Path,
    dflowfm_dll: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    metaswap_lookup_table: Path,
    reference_result_folder: Path,
    imod_coupler_exec_devel: Path,
) -> None:
    """
    This test aims to remove all the exchanges that involve dflow, so that we can compare the result of
    the simulation with the metamod driver's result for the same setup.
    """
    shutil.copytree(tmodel_f_input_folder, tmp_path_dev)
    toml_file_path = tmp_path_dev / "imod_coupler.toml"
    output_config_path = tmp_path_dev / "output_config.toml"

    set_toml_file_tmodel(
        toml_file_path,
        modflow_dll_devel,
        metaswap_dll_devel,
        metaswap_dll_dep_dir_devel,
        dflowfm_dll,
    )
    files_to_skip = {
        "msw_ponding_to_dfm_2d_dv_dmm",
        "dfm_2d_waterlevels_to_msw_h_dmm",
        "mf6_river2_to_dmf_1d_q_dmm",
        "mf6_drainage_to_dfm_1d_q_dmm",
        "msw_sprinkling_to_dfm_1d_q_dmm",
        "msw_runoff_to_dfm_1d_q_dmm",
        "mf6_river_to_dfm_1d_q_dmm",
        "dfm_1d_waterlevel_to_mf6_river_stage_dmm",
        "mf6_msw_sprinkling_map",
        "mf6_msw_well_pkg",
    }

    remove_exchange_file_references(toml_file_path, files_to_skip)

    set_workdir_in_logging_config_file(output_config_path, tmp_path_dev)
    fill_para_sim_template(tmp_path_dev / "MetaSWAP", metaswap_lookup_table)

    subprocess.run(
        [str(imod_coupler_exec_devel), toml_file_path],
        check=True,
    )
