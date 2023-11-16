from pathlib import Path

import numpy as np
from imod import mf6
from numpy.typing import NDArray

from imod_coupler.kernelwrappers.mf6_wrapper import Mf6Drainage, Mf6River, Mf6Wrapper


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

    stage_address = mf6wrapper.get_var_address("STAGE", "GWF_1", "Oosterschelde")
    stage = mf6wrapper.get_value_ptr(stage_address)

    np.testing.assert_allclose(stage, new_river_stage)
    mf6wrapper.finalize()


def test_mf6_river(
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

    mf6_river = Mf6River(
        mf6_wrapper=mf6wrapper,
        mf6_flowmodel_key="GWF_1",
        mf6_pkg_key="Oosterschelde",
    )
    # The nodelist should be set properly after prepare_time_step.
    mf6_river.get_nodelist()

    # The nodelist should be set after
    assert (mf6_river.nodelist != -1).any()

    # This guards against setting below elevation.
    mf6_river.set_stage(-123.0)
    stage_address = mf6wrapper.get_var_address("STAGE", "GWF_1", "Oosterschelde")
    stage = mf6wrapper.get_value_ptr(stage_address)
    assert (stage > -10.0).all()

    # This accesses directly.
    mf6_river.stage[:] = -123.0
    stage_address = mf6wrapper.get_var_address("STAGE", "GWF_1", "Oosterschelde")
    stage = mf6wrapper.get_value_ptr(stage_address)
    np.testing.assert_allclose(stage, -123.0)
    mf6wrapper.finalize()


def test_mf6_drainage(
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

    mf6_drainage = Mf6Drainage(
        mf6_wrapper=mf6wrapper,
        mf6_flowmodel_key="GWF_1",
        mf6_pkg_key="Drainage",
    )
    mf6_drainage.get_nodelist()

    # The nodelist should be set properly after prepare_time_step.
    assert (mf6_drainage.nodelist != -1).any()

    # This guards against setting below elevation.
    mf6_drainage.set_elevation(-123.0)
    elev_address = mf6wrapper.get_var_address("ELEV", "GWF_1", "Drainage")
    elev = mf6wrapper.get_value_ptr(elev_address)
    assert (elev > -10.0).all()

    # This accesses directly.
    mf6_drainage.elevation[:] = -123.0
    elev_address = mf6wrapper.get_var_address("ELEV", "GWF_1", "Drainage")
    elev = mf6wrapper.get_value_ptr(elev_address)
    np.testing.assert_allclose(elev, -123.0)
    mf6wrapper.finalize()


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
