import subprocess
from pathlib import Path

import pytest
from imod.msw import MetaSwapModel
from primod.ribamod import RibaMod
from pytest_cases import parametrize_with_cases


@pytest.mark.xdist_group(name="ribasim")
@parametrize_with_cases("ribametamod_model", glob="bucket_model")
def test_ribametamod_develop(
    tmp_path_dev: Path,
    ribametamod_model: RibaMod | MetaSwapModel,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    imod_coupler_exec_devel: Path,
) -> None:
    """
    Test if coupled ribametamod models run with the iMOD Coupler development version.
    """
    ribamod_model, msw_model = ribametamod_model
    ribamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        ribasim_dll=ribasim_dll_devel,
        ribasim_dll_dependency=ribasim_dll_dep_dir_devel,
    )
    msw_model.write(
        tmp_path_dev / "metaswap"
    )  # the RibaMetaMod should do this eventually

    subprocess.run(
        [imod_coupler_exec_devel, tmp_path_dev / ribamod_model._toml_name], check=True
    )


@pytest.mark.xdist_group(name="ribasim")
@parametrize_with_cases("ribametamod_model", glob="bucket_model")
def test_ribametamod_bucket(
    tmp_path_dev: Path,
    ribametamod_model: RibaMod | MetaSwapModel,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    imod_coupler_exec_devel: Path,
) -> None:
    """
    Test if the bucket model works as expected
    """
    ribamod_model, msw_model = ribametamod_model
    ribamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        ribasim_dll=ribasim_dll_devel,
        ribasim_dll_dependency=ribasim_dll_dep_dir_devel,
    )
    msw_model.write(
        tmp_path_dev / "metaswap"
    )  # the RibaMetaMod should do this eventually
    subprocess.run(
        [imod_coupler_exec_devel, tmp_path_dev / ribamod_model._toml_name], check=True
    )
    # TODO: add checks on output if RibaMetaMod class is implemented


@pytest.mark.skip(
    reason="imod-python’s MetaSWAP model does not accept negative coords currently. Skip until issue #812 is merged in imod-python "
)
@parametrize_with_cases("ribametamod_model", glob="backwater_model")
def test_ribametamod_backwater(
    tmp_path_dev: Path,
    ribametamod_model: RibaMod | MetaSwapModel,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    imod_coupler_exec_devel: Path,
) -> None:
    """
    Test if the backwater model works as expected
    """
    ribamod_model, msw_model = ribametamod_model
    ribamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        ribasim_dll=ribasim_dll_devel,
        ribasim_dll_dependency=ribasim_dll_dep_dir_devel,
    )
    msw_model.write(
        tmp_path_dev / "metaswap"
    )  # the RibaMetaMod should do this eventually
    subprocess.run(
        [imod_coupler_exec_devel, tmp_path_dev / ribamod_model._toml_name], check=True
    )
    # TODO: add checks on output if RibaMetaMod class is implemented


@pytest.mark.skip(
    reason="imod-python’s MetaSWAP model does not accept negative coords currently. Skip until issue #812 is merged in imod-python"
)
@parametrize_with_cases("ribametamod_model", glob="two_basin_model")
def test_ribametamod_two_basin(
    tmp_path_dev: Path,
    ribametamod_model: RibaMod | MetaSwapModel,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    imod_coupler_exec_devel: Path,
) -> None:
    """
    Test if the two-basin model model works as expected
    """
    ribamod_model, msw_model = ribametamod_model
    ribamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        ribasim_dll=ribasim_dll_devel,
        ribasim_dll_dependency=ribasim_dll_dep_dir_devel,
    )
    msw_model.write(
        tmp_path_dev / "metaswap"
    )  # the RibaMetaMod should do this eventually
    subprocess.run(
        [imod_coupler_exec_devel, tmp_path_dev / ribamod_model._toml_name], check=True
    )
    # TODO: add checks on output if RibaMetaMod class is implemented
