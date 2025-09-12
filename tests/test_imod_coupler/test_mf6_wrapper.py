from pathlib import Path

import numpy as np
from imod import mf6

from imod_coupler.kernelwrappers.mf6_wrapper import Mf6Drainage, Mf6River, Mf6Wrapper


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
    mf6_river.set_private_nodelist()

    # The nodelist should be set after
    assert (mf6_river.nodelist != -1).any()

    # This guards against setting below elevation.
    mf6_river.set_water_level(np.full_like(mf6_river.water_level, -123.0))
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
    mf6_drainage.set_private_nodelist()

    # The nodelist should be set properly after prepare_time_step.
    assert (mf6_drainage.private_nodelist != -1).any()

    # This guards against setting below elevation.
    mf6_drainage.set_water_level(np.full_like(mf6_drainage.water_level, -123.0))
    elev_address = mf6wrapper.get_var_address("ELEV", "GWF_1", "Drainage")
    elev = mf6wrapper.get_value_ptr(elev_address)
    assert (elev > -10.0).all()

    # This accesses directly.
    mf6_drainage.elevation[:] = -123.0
    elev_address = mf6wrapper.get_var_address("ELEV", "GWF_1", "Drainage")
    elev = mf6wrapper.get_value_ptr(elev_address)
    np.testing.assert_allclose(elev, -123.0)
    mf6wrapper.finalize()
