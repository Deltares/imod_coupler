import shutil
import subprocess
from pathlib import Path
from typing import Dict, Set, Tuple

import pytest
from fixtures.fixture_model import (
    remove_exchange_file_references,
    run_waterbalance_script_on_tmodel,
    set_toml_file_tmodel,
    set_workdir_in_logging_config_file,
)
from pytest_cases import parametrize_with_cases
from test_utilities import fill_para_sim_template, numeric_csvfiles_equal

from imod_coupler.__main__ import run_coupler

sep = ";"


@parametrize_with_cases(
    "tmodel_input_folder,files_to_skip,mf6_model_rootname,csv_reference_filename,tolerance_balance",
    prefix="case_tmodel_",
)
def test_run_tmodel(
    tmp_path_dev: Path,
    modflow_dll_devel: Path,
    dflowfm_dll: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    metaswap_lookup_table: Path,
    reference_result_folder: Path,
    imod_coupler_exec_devel: Path,
    tmodel_input_folder: Path,
    files_to_skip: Set[str],
    mf6_model_rootname: str,
    csv_reference_filename: str,
    tolerance_balance: Dict[str, Tuple[float, float]],
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

    
    remove_exchange_file_references(toml_file_path, files_to_skip)

    set_workdir_in_logging_config_file(output_config_path, tmp_path_dev)
    fill_para_sim_template(tmp_path_dev / "MetaSWAP", metaswap_lookup_table)

    subprocess.run(
        [imod_coupler_exec_devel, toml_file_path],
        check=True,)
    
    waterbalance_result = run_waterbalance_script_on_tmodel(
        tmp_path_dev, mf6_model_rootname
    )
    csv_reference_file = (
        reference_result_folder / "test_run_tmodel" / csv_reference_filename
    )
    if csv_reference_file.exists():
        assert numeric_csvfiles_equal(
            waterbalance_result,
            csv_reference_file,
            sep,
            tolerance_balance,
        )


@pytest.mark.maintenance
def test_run_tmodel_f_with_metamod(
    tmp_path_dev: Path,
    test_data_folder: Path,
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

    tmodel_input_folder = test_data_folder / "t_model_f"
    shutil.copytree(tmodel_input_folder, tmp_path_dev)
    toml_file_path = tmp_path_dev / "metamod.toml"

    set_toml_file_tmodel(
        toml_file_path,
        modflow_dll_devel,
        metaswap_dll_devel,
        metaswap_dll_dep_dir_devel,
    )

    fill_para_sim_template(tmp_path_dev / "MetaSWAP", metaswap_lookup_table)

    subprocess.run(
        [imod_coupler_exec_devel, toml_file_path],
        check=True,
    )
