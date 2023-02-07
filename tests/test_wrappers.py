import os
import shutil
from pathlib import Path

import pytest
from bmi.wrapper import BMIWrapper
from dfm_test_initialization import copy_inputfiles, set_dfm_path
from hydrolib.core.dflowfm.mdu.models import FMModel
from imod import mf6
from xmipy import XmiWrapper


@pytest.mark.skip("test is unstable.")
def test_bmi_wrapper_can_be_initialized_and_finalized_multiple_times(
    prepared_dflowfm_model: FMModel,
    dflowfm_dll_devel: Path,
    dflowfm_initial_inputfiles_folder: Path,
) -> None:
    prepared_dflowfm_model.save(recurse=True)

    set_dfm_path(dflowfm_dll_devel)

    copy_inputfiles(
        dflowfm_initial_inputfiles_folder, prepared_dflowfm_model.filepath.parent
    )

    bmiwrapper = BMIWrapper(
        engine="dflowfm", configfile=prepared_dflowfm_model.filepath
    )

    bmiwrapper.initialize()
    bmiwrapper.finalize()
    bmiwrapper.initialize()
    bmiwrapper.finalize()


def test_xmi_wrapper_can_be_initialized_and_finalized_multiple_times(
    mf6_model_with_river: mf6.Modflow6Simulation,
    modflow_dll_regression: Path,
    tmp_path_dev: Path,
) -> None:
    mf6_model_with_river.write(tmp_path_dev)
    mf6wrapper = XmiWrapper(
        lib_path=modflow_dll_regression,
        working_directory=tmp_path_dev,
    )
    mf6wrapper.initialize()
    mf6wrapper.finalize()
    mf6wrapper.initialize()
    mf6wrapper.finalize()
