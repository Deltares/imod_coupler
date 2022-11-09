import os
import shutil
from pathlib import Path

import numpy as np
import pytest
from dfm_test_initialization import copy_inputfiles, set_dfm_path
from hydrolib.core.io.mdu.models import FMModel
from numpy.testing import assert_array_equal

from imod_coupler.drivers.dfm_metamod.dfm_wrapper import DfmWrapper


def test_get_river_stage_from_dflow(
    prepared_dflowfm_model: FMModel,
    dflowfm_dll_devel: Path,
    dflowfm_initial_inputfiles_folder: Path,
) -> None:

    prepared_dflowfm_model.save(recurse=True)

    set_dfm_path(dflowfm_dll_devel)
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



def test_get_snapped_flownode(
    prepared_dflowfm_model: FMModel,
    dflowfm_dll_devel: Path,
    dflowfm_initial_inputfiles_folder: Path,
) -> None:

    prepared_dflowfm_model.save(recurse=True)

    set_dfm_path(dflowfm_dll_devel)
    copy_inputfiles(
        dflowfm_initial_inputfiles_folder, prepared_dflowfm_model.filepath.parent
    )

    bmiwrapper = DfmWrapper(
        engine="dflowfm", configfile=prepared_dflowfm_model.filepath
    )

    bmiwrapper.initialize()
    input_node_x = np.array([150.0, 150.0, 450.0])
    input_node_y = np.array([150.0, 250.0, 250.0])
    flownode_ids = bmiwrapper.get_snapped_flownode(input_node_x, input_node_y)
    bmiwrapper.finalize()

    excepted_flownode_ids = np.array([1, 2, 8])
    assert_array_equal(
        flownode_ids,
        excepted_flownode_ids,
    )
