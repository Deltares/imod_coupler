import shutil
from pathlib import Path

import numpy as np
from dfm_test_initialization import set_dfm_path
from numpy.testing import assert_array_equal

from imod_coupler.drivers.dfm_metamod.dfm_wrapper import DfmWrapper


def test_get_river_stage(
    tmodel_input_folder: Path,
    dflowfm_dll_regression: Path,
    tmp_path_reg: Path,
) -> None:
    shutil.copytree(tmodel_input_folder / "dflow-fm", tmp_path_reg)
    set_dfm_path(dflowfm_dll_regression)

    bmiwrapper = DfmWrapper(engine="dflowfm", configfile=tmp_path_reg / "FlowFM.mdu")

    bmiwrapper.initialize()
    bmiwrapper.update()
    water_levels_1d = bmiwrapper.get_waterlevels_1d()
    bmiwrapper.finalize()

    assert water_levels_1d is not None
    assert len(water_levels_1d) == 20
    reference_result = np.array(
        [
            10.05267912,
            10.05255347,
            10.05247691,
            10.05241757,
            10.05239327,
            10.05244195,
            10.05224224,
            10.05142698,
            10.0504504,
            10.04934978,
            10.04812866,
            10.04687276,
            10.04610396,
            9.133569,
            9.13208469,
            9.11029247,
            9.05359345,
            9.0,
            10.05325025,
            10.05244195,
        ]
    )
    np.testing.assert_almost_equal(water_levels_1d, reference_result)


def test_get_cumulative_fluxes_1d_nodes(
    tmodel_input_folder: Path,
    dflowfm_dll_regression: Path,
    tmp_path_reg: Path,
) -> None:

    shutil.copytree(tmodel_input_folder / "dflow-fm", tmp_path_reg)
    set_dfm_path(dflowfm_dll_regression)
    bmiwrapper = DfmWrapper(engine="dflowfm", configfile=tmp_path_reg / "FlowFM.mdu")

    bmiwrapper.initialize()
    bmiwrapper.update()

    cumul_fluxes = bmiwrapper.get_cumulative_fluxes_1d_nodes()
    bmiwrapper.finalize()
    assert cumul_fluxes is not None
    assert len(cumul_fluxes) == 20
    # @TODO
    # check if these cumulative fluxes are supposed to be zero
    np.testing.assert_allclose(cumul_fluxes, 0)




def test_get_1d_river_fluxes(
    tmodel_input_folder: Path,
    dflowfm_dll_regression: Path,
    tmp_path_reg: Path,
) -> None:

    shutil.copytree(tmodel_input_folder / "dflow-fm", tmp_path_reg)
    set_dfm_path(dflowfm_dll_regression)

    bmiwrapper = DfmWrapper(
        engine="dflowfm", configfile=tmodel_input_folder / "dflow-fm" / "FlowFM.mdu"
    )

    bmiwrapper.initialize()
    bmiwrapper.update()
    fluxes = bmiwrapper.get_1d_river_fluxes()
    assert fluxes is not None
    fluxes[:] = 20
    bmiwrapper.set_1d_river_fluxes(fluxes)
    new_fluxes = bmiwrapper.get_1d_river_fluxes()
    bmiwrapper.finalize()
    assert new_fluxes is not None
    np.testing.assert_allclose(fluxes, new_fluxes)


def test_set_1d_river_fluxes(
    tmodel_input_folder: Path,
    dflowfm_dll_regression: Path,
    tmp_path_reg: Path,
) -> None:

    shutil.copytree(tmodel_input_folder / "dflow-fm", tmp_path_reg)
    set_dfm_path(dflowfm_dll_regression)

    bmiwrapper = DfmWrapper(engine="dflowfm", configfile=tmp_path_reg / "FlowFM.mdu")

    bmiwrapper.initialize()
    bmiwrapper.update()
    fluxes = bmiwrapper.get_1d_river_fluxes()
    assert fluxes is not None
    fluxes[:] = 20
    bmiwrapper.set_1d_river_fluxes(fluxes)
    new_fluxes = bmiwrapper.get_1d_river_fluxes()
    bmiwrapper.finalize()
    assert new_fluxes is not None
    np.testing.assert_allclose(fluxes, new_fluxes)




def test_get_snapped_flownode(
    prepared_dflowfm_model: FMModel,
    dflowfm_dll_devel: Path,
    dflowfm_initial_inputfiles_folder: Path,
) -> None:

    prepared_dflowfm_model.save(recurse=True)

    set_dfm_path(dflowfm_dll_devel)

    bmiwrapper = DfmWrapper(engine="dflowfm", configfile=tmp_path_reg / "FlowFM.mdu")

    bmiwrapper.initialize()
    bmiwrapper.update()
    fluxes = bmiwrapper.get_1d_river_fluxes()
  )
def test_set_1d_river_fluxes(
    tmodel_input_folder: Path,
    dflowfm_dll_regression: Path,
    tmp_path_reg: Path,
) -> None:

    shutil.copytree(tmodel_input_folder / "dflow-fm", tmp_path_reg)
    set_dfm_path(dflowfm_dll_regression)

    bmiwrapper = DfmWrapper(engine="dflowfm", configfile=tmp_path_reg / "FlowFM.mdu")

    bmiwrapper.initialize()
    bmiwrapper.update()
    fluxes = bmiwrapper.get_1d_river_fluxes()
    assert fluxes is not None
    fluxes[:] = 20
    bmiwrapper.set_1d_river_fluxes(fluxes)
    new_fluxes = bmiwrapper.get_1d_river_fluxes()
    bmiwrapper.finalize()
    assert new_fluxes is not None
    np.testing.assert_allclose(fluxes, new_fluxes)
    

    shutil.copytree(tmodel_input_folder / "dflow-fm", tmp_path_reg)
    set_dfm_path(dflowfm_dll_regression)

    bmiwrapper = DfmWrapper(engine="dflowfm", configfile=tmp_path_reg / "FlowFM.mdu")

    bmiwrapper.initialize()
    bmiwrapper.update()
    fluxes = bmiwrapper.get_1d_river_fluxes()
    assert fluxes is not None
    fluxes[:] = 20
    bmiwrapper.set_1d_river_fluxes(fluxes)
    new_fluxes = bmiwrapper.get_1d_river_fluxes()
    bmiwrapper.finalize()
    assert new_fluxes is not None
    np.testing.assert_allclose(fluxes, new_fluxes)
