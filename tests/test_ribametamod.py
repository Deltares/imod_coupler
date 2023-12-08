import shutil
import subprocess
from pathlib import Path

import pytest
import tomli_w
from primod.ribamod import RibaMod
from pytest_cases import parametrize_with_cases


@pytest.mark.xdist_group(name="ribasim")
@parametrize_with_cases("ribamod_model", glob="bucket_model")
def test_ribametamod_bucket(
    tmp_path_dev: Path,
    ribamod_model: RibaMod,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    imod_coupler_exec_devel: Path,
) -> None:
    """
    Test if the bucket model works as expected
    """
    ribamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        ribasim_dll=ribasim_dll_devel,
        ribasim_dll_dependency=ribasim_dll_dep_dir_devel,
    )

    subprocess.run(
        [imod_coupler_exec_devel, tmp_path_dev / ribamod_model._toml_name], check=True
    )
