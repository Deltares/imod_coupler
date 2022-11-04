import tempfile
from pathlib import Path

import numpy as np
from imod import mf6
from numpy.typing import NDArray
from xmipy import XmiWrapper

from imod_coupler.drivers.dfm_metamod.mf6_utilities import MF6Utilities


def test_mf6_set_river_stage(
    mf6_model_with_river: mf6.Modflow6Simulation, modflow_dll_regression: Path
) -> None:

    testdir = tempfile.mkdtemp()

    mf6_model_with_river.write(testdir)
    mf6wrapper = XmiWrapper(
        lib_path=modflow_dll_regression,
        working_directory=testdir,
    )
    mf6wrapper.initialize()
    mf6wrapper.prepare_time_step(0.0)

    new_river_stage = NDArray[np.float_](15)
    new_river_stage[:] = range(15)
    MF6Utilities.set_river_stages(
        mf6wrapper,
        "GWF_1",
        "Oosterschelde",
        new_river_stage,
    )

    bound_adress = mf6wrapper.get_var_address("BOUND", "GWF_1", "Oosterschelde")
    bound = mf6wrapper.get_value_ptr(bound_adress)
    stage = bound[:, 0]
    assert np.isclose(stage, new_river_stage).all()
