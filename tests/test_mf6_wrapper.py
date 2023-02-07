import tempfile
from pathlib import Path

import numpy as np
from imod import mf6
from numpy.typing import NDArray
from xmipy import XmiWrapper

from imod_coupler.drivers.dfm_metamod.mf6_wrapper import Mf6Wrapper


def test_mf6_set_river_stage(
    mf6_model_with_river: mf6.Modflow6Simulation,
    modflow_dll_devel: Path,
    tmp_path_dev: Path,
) -> None:
    mf6_model_with_river.write(tmp_path_dev)

    mf6wrapper = Mf6Wrapper(
        lib_path=modflow_dll_devel,
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


def test_mf6_get_river_flux(
    mf6_model_with_river: mf6.Modflow6Simulation,
    modflow_dll_devel: Path,
    tmp_path_dev: Path,
) -> None:
    mf6_model_with_river.write(tmp_path_dev)
    mf6wrapper = Mf6Wrapper(
        lib_path=modflow_dll_devel,
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

    q = mf6wrapper.get_river_flux_estimate("GWF_1", "Oosterschelde")

    np.testing.assert_allclose(
        q,
        np.array(
            [
                -1.26,
                2.94,
                8.82,
                11.34,
                15.54,
                19.74,
                23.94,
                29.82,
                32.34,
                36.54,
                40.74,
                44.94,
                50.82,
                53.34,
                57.54,
            ]
        ),
    )
