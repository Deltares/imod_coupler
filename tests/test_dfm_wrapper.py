import os
from pathlib import Path

import numpy as np
import pytest
from dfm_test_initialization import copy_inputfiles, set_dfm_path
from hydrolib.core.io.mdu.models import FMModel

from imod_coupler.drivers.dfm_metamod.dfm_wrapper import DfmWrapper


# @pytest.mark.skip(
#     reason="currently the BMI wrapper does not survive a second initialize call, and it was already used in test_dfm_metamod"
#     + "It should still work when running just this test."
# )
def test_get_river_stage_from_dflow(
    prepared_dflowfm_model: FMModel,
    dflowfm_dll_regression: Path,
    dflowfm_initial_inputfiles_folder: Path,
    tmp_path_reg: Path,
) -> None:

    prepared_dflowfm_model.save(recurse=True)
    prepared_dflowfm_model.filepath = tmp_path_reg / "fm.mdu"

    set_dfm_path(dflowfm_dll_regression)
    copy_inputfiles(
        dflowfm_initial_inputfiles_folder, prepared_dflowfm_model.filepath.parent
    )

    bmiwrapper = DfmWrapper(
        engine="dflowfm", configfile=prepared_dflowfm_model.filepath
    )

    bmiwrapper.initialize()
    water_levels_1d = bmiwrapper.get_waterlevels_1d()
    bmiwrapper.finalize()

    # the current test dataset does not have 1d rivers.
    assert water_levels_1d is None


def test_get_snapped_feature(
    prepared_dflowfm_model: FMModel,
    dflowfm_dll_regression: Path,
    dflowfm_initial_inputfiles_folder: Path,
    tmp_path_reg: Path,
) -> None:

    prepared_dflowfm_model.save(recurse=True)
    prepared_dflowfm_model.filepath = tmp_path_reg / "fm.mdu"

    set_dfm_path(dflowfm_dll_regression)
    copy_inputfiles(
        dflowfm_initial_inputfiles_folder, prepared_dflowfm_model.filepath.parent
    )

    bmiwrapper = DfmWrapper(
        engine="dflowfm", configfile=prepared_dflowfm_model.filepath
    )

    bmiwrapper.initialize()
    input_node_x = np.array([200.0])
    input_node_y = np.array([200.0])
    result = bmiwrapper.get_snapped_flownode(input_node_x, input_node_y)
    bmiwrapper.finalize()

    assert result == 1
