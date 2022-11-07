import os
from pathlib import Path

import pytest
from dfm_test_initialization import copy_inputfiles, set_dfm_path
from hydrolib.core.io.mdu.models import FMModel

from imod_coupler.drivers.dfm_metamod.dfm_wrapper import DfmWrapper


@pytest.mark.skip(
    reason="currently the BMI wrapper does not survive a second initialize call, and it was already used in test_dfm_metamod"
    + "It should still work when running just this test."
)
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
    assert water_levels_1d is not None
    assert len(water_levels_1d) == 0
