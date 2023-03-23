import shutil
import subprocess
from pathlib import Path
from typing import Set

import tomli
import tomli_w
from pytest_cases import parametrize_with_cases
from test_utilities import fill_para_sim_template

from tests.fixtures.fixture_model import (
    remove_exchange_file_references,
    set_kernels_paths_into_toml_file,
)


@parametrize_with_cases("files_to_skip", prefix="case_skiptest_")
def test_run_tmodel_not_all_exchanges(
    tmp_path_dev: Path,
    tmodel_short_input_folder: Path,
    modflow_dll_devel: Path,
    dflowfm_dll: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    metaswap_lookup_table: Path,
    files_to_skip: Set[str],
    imod_coupler_exec_devel: Path,
) -> None:
    shutil.copytree(tmodel_short_input_folder, tmp_path_dev)

    toml_file_path = tmp_path_dev / "imod_coupler.toml"
    toml_dict = {}

    set_kernels_paths_into_toml_file(
        toml_file_path,
        modflow_dll_devel,
        dflowfm_dll,
        metaswap_dll_devel,
        metaswap_dll_dep_dir_devel,
    )

    remove_exchange_file_references(toml_file_path, files_to_skip)

    for filekey in files_to_skip:
        toml_dict["driver"]["coupling"][0].pop(filekey, None)

    with open(toml_file_path, "wb") as toml_file:
        tomli_w.dump(toml_dict, toml_file)

    fill_para_sim_template(tmp_path_dev / "MetaSWAP", metaswap_lookup_table)

    subprocess.run(
        [imod_coupler_exec_devel, toml_file_path],
        check=True,
    )
