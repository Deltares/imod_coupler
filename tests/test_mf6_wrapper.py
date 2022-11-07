import tempfile
from pathlib import Path

import numpy as np
from imod import mf6
from numpy.typing import NDArray
from xmipy import XmiWrapper

from imod_coupler.drivers.dfm_metamod.mf6_wrapper import Mf6Wrapper


def test_mf6_set_river_stage(
    mf6_model_with_river: mf6.Modflow6Simulation,
    modflow_dll_regression: Path,
    tmp_path_dev: Path,
) -> None:

    mf6_model_with_river.write(tmp_path_dev)
    mf6wrapper = Mf6Wrapper(
        lib_path=modflow_dll_regression,
        working_directory=tmp_path_dev,
    )
    mf6wrapper.initialize()
    mf6wrapper.prepare_time_step(0.0)

    new_river_stage = NDArray[np.float_](15)
    new_river_stage[:] = range(15)
    mf6wrapper.set_river_stages(
        "GWF_1",
        "Oosterschelde",
        new_river_stage,
    )

    bound_adress = mf6wrapper.get_var_address("BOUND", "GWF_1", "Oosterschelde")
    bound = mf6wrapper.get_value_ptr(bound_adress)
    stage = bound[:, 0]

    np.testing.assert_allclose(stage, new_river_stage)
    mf6wrapper.finalize()