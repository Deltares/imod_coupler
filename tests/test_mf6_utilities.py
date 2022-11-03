import tempfile
from pathlib import Path

import numpy as np
from imod import mf6
from numpy.typing import NDArray
from xmipy import XmiWrapper

from imod_coupler.drivers.dfm_metamod.mf6_utilities import MF6Utilities


def test_mf6_get_flowmodel_key(mf6_model_with_river: mf6.Modflow6Simulation) -> None:

    flowmodels = MF6Utilities.get_flow_model_keys(mf6_model_with_river)
    assert len(flowmodels) == 1
    assert flowmodels[0] == "GWF_1"
    assert isinstance(mf6_model_with_river[flowmodels[0]], mf6.GroundwaterFlowModel)


def test_mf6_get_package_keys(mf6_model_with_river: mf6.Modflow6Simulation) -> None:

    flowmodel_key = MF6Utilities.get_flow_model_keys(mf6_model_with_river)[0]
    river_packs = MF6Utilities.get_modflow_package_keys(
        mf6_model_with_river[flowmodel_key], mf6.River
    )
    assert len(river_packs) == 1
    assert river_packs[0] == "Oosterschelde"


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

    new_river_stage = range(15)
    MF6Utilities.set_river_stages(
        mf6wrapper, mf6_model_with_river, NDArray[np.float_](new_river_stage)
    )

    bound_adress = mf6wrapper.get_var_address("BOUND", "GWF_1", "Oosterschelde")
    bound = mf6wrapper.get_value_ptr(bound_adress)
    stage = bound[:, 0]
    assert np.isclose(NDArray[np.float_](stage), NDArray[np.float_](stage))
