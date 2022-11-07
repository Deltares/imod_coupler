import shutil
from os import listdir
from pathlib import Path

import pytest
from dfm_test_initialization import copy_inputfiles
from pytest_cases import parametrize_with_cases

from imod_coupler.__main__ import run_coupler
from imod_coupler.drivers.dfm_metamod.dfm_metamod_model import DfmMetaModModel


@parametrize_with_cases("dfm_metamod", prefix="case_")
def test_dfmmetamod_initialization(
    dfm_metamod: DfmMetaModModel,
    modflow_dll_devel: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    dflowfm_dll: Path,
    dflowfm_initial_inputfiles_folder: Path,
    tmp_path_dev: Path,
):
    # write input for the simulators and a toml configuration file containing the paths of these
    # inputfiles and the paths of the kernel dll's
    dfm_metamod.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
        dflowfm_dll=dflowfm_dll,
    )

    copy_inputfiles(dflowfm_initial_inputfiles_folder, tmp_path_dev / "dflow-fm")

    inputpath = tmp_path_dev / dfm_metamod._toml_name

    # at this stage, imod_coupler is unable to complete the run with these 3 models and kernels.
    # so we check we get an exception that originates in the "couple" method - getting there
    # means the initialization of the kernels went well.
    with pytest.raises(ValueError) as e:
        run_coupler(inputpath)
    assert str(e.value) == "Expected size of new_river_stages is 15"
