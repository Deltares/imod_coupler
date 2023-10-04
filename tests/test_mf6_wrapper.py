from pathlib import Path

import numpy as np
import pytest
from imod import mf6
from numpy.typing import NDArray

from imod_coupler.kernelwrappers.mf6_wrapper import Mf6Wrapper


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


@pytest.mark.skip(
    "MODFLOW 6 internals changed, we should enable this test again as soon as possible"
)
def test_mf6_get_river_flux_estimate(
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
    mf6wrapper.prepare_solve(1)

    # now first solve, because "get_river_drain_flux" needs the actual solution to be formulated.
    max_iter = mf6wrapper.get_value_ptr("SLN_1/MXITER")[0]
    for _ in range(1, max_iter + 1):
        has_converged = mf6wrapper.solve(1)
        if has_converged:
            break
    q = mf6wrapper.get_river_drain_flux("GWF_1", "Oosterschelde")
    q_expected = np.array(
        [
            -0.0,
            10.654179,
            10.402491,
            10.396607,
            10.396469,
            -0.0,
            10.654179,
            10.402491,
            10.396607,
            10.396469,
            -0.0,
            10.654179,
            10.402491,
            10.396607,
            10.396469,
        ]
    )
    np.testing.assert_allclose(q, q_expected)
