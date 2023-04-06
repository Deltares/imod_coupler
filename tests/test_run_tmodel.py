import shutil
import subprocess
from pathlib import Path

import pytest
from fixtures.fixture_model import (
    evaluate_waterbalance,
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
        dflowfm_dll,
        metaswap_dll_devel,
        metaswap_dll_dep_dir_devel,
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
        dflowfm_dll,
        metaswap_dll_devel,
        metaswap_dll_dep_dir_devel,
    )

    set_workdir_in_logging_config_file(output_config_path, tmp_path_dev)
    fill_para_sim_template(tmp_path_dev / "MetaSWAP", metaswap_lookup_table)

    #run_coupler(toml_file_path)
    evaluate_waterbalance(tmp_path_dev, reference_result_folder, "T-MODEL-F.LST")
    subprocess.run(
      [str(imod_coupler_exec_devel), toml_file_path],
      check=True,
    )
