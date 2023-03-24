import shutil
import subprocess
from pathlib import Path

import pytest
from fixtures.fixture_model import (
    evaluate_waterbalance,
    remove_exchange_file_references,
    set_toml_file_tmodel,
    set_workdir_in_logging_config_file,
)
from test_utilities import fill_para_sim_template, numeric_csvfiles_equal

from imod_coupler.__main__ import run_coupler


def test_run_tmodel(
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

    set_workdir_in_logging_config_file(output_config_path, tmp_path_dev)
    fill_para_sim_template(tmp_path_dev / "MetaSWAP", metaswap_lookup_table)

    subprocess.run(
        [imod_coupler_exec_devel, toml_file_path],
        check=True,
    )
    evaluate_waterbalance(tmp_path_dev, reference_result_folder, "T-MODEL-D.LST")


def test_run_tmodel_f(
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

    set_workdir_in_logging_config_file(output_config_path, tmp_path_dev)
    fill_para_sim_template(tmp_path_dev / "MetaSWAP", metaswap_lookup_table)

    subprocess.run(
        [str(imod_coupler_exec_devel), toml_file_path],
        check=True,
    )


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
    shutil.copytree(tmodel_f_input_folder, tmp_path_dev)
    toml_file_path = tmp_path_dev / "metamod.toml"
    output_config_path = tmp_path_dev / "output_config.toml"

    set_toml_file_tmodel(
        toml_file_path,
        modflow_dll_devel,
        metaswap_dll_devel,
        metaswap_dll_dep_dir_devel,
    )

    fill_para_sim_template(tmp_path_dev / "MetaSWAP", metaswap_lookup_table)

    run_coupler(toml_file_path)
    """ subprocess.run(
        [str(imod_coupler_exec_devel), toml_file_path],
        check=True,
    )   """


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
    }
    remove_exchange_file_references(toml_file_path, files_to_skip)

    set_workdir_in_logging_config_file(output_config_path, tmp_path_dev)
    fill_para_sim_template(tmp_path_dev / "MetaSWAP", metaswap_lookup_table)

    run_coupler(toml_file_path)
    """ subprocess.run(
        [str(imod_coupler_exec_devel), toml_file_path],
        check=True,
    )   """
