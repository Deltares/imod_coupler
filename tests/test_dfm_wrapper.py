import os
import shutil
from pathlib import Path

import numpy as np
from dfm_test_initialization import copy_inputfiles, set_dfm_path
from hydrolib.core.dflowfm.mdu.models import FMModel
from numpy.testing import assert_array_equal

from imod_coupler.drivers.dfm_metamod.dfm_wrapper import DfmWrapper


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


def test_get_river_stage(
    tmodel_input_folder: Path,
    dflowfm_dll_devel: Path,
    tmp_path_dev: Path,
) -> None:
    shutil.copytree(tmodel_input_folder / "dflow-fm", tmp_path_dev)
    set_dfm_path(dflowfm_dll_devel)

    bmiwrapper = DfmWrapper(engine="dflowfm", configfile=tmp_path_dev / "FlowFM.mdu")

    bmiwrapper.initialize()
    bmiwrapper.update()
    water_levels_1d = bmiwrapper.get_waterlevels_1d_ptr()
    bmiwrapper.finalize()

    assert water_levels_1d is not None
    assert len(water_levels_1d) == 20
    reference_result = np.array(
        [
            10.05412232,
            10.05367417,
            10.05316315,
            10.0526756,
            10.05226328,
            10.05217788,
            10.05211877,
            10.05208595,
            10.05203286,
            10.05199938,
            10.05121906,
            10.05021786,
            10.04904483,
            10.04767879,
            10.04616922,
            10.04497164,
            9.16042689,
            9.15877603,
            9.13318928,
            9.06684356,
        ]
    )
    np.testing.assert_allclose(water_levels_1d, reference_result, rtol=1e-3)


def test_get_cumulative_fluxes_1d_nodes(
    tmodel_input_folder: Path,
    dflowfm_dll_devel: Path,
    tmp_path_dev: Path,
) -> None:
    shutil.copytree(tmodel_input_folder / "dflow-fm", tmp_path_dev)
    set_dfm_path(dflowfm_dll_devel)

    bmiwrapper = DfmWrapper(engine="dflowfm", configfile=tmp_path_dev / "FlowFM.mdu")

    bmiwrapper.initialize()
    bmiwrapper.update()

    cumul_fluxes = bmiwrapper.get_cumulative_fluxes_1d_nodes_ptr()
    bmiwrapper.finalize()
    assert cumul_fluxes is not None
    assert len(cumul_fluxes) == 20
    # @TODO
    # check if these cumulative fluxes are supposed to be zero
    np.testing.assert_allclose(cumul_fluxes, 0)


def test_get_1d_river_fluxes_ptr(
    tmodel_input_folder: Path,
    dflowfm_dll_devel: Path,
    tmp_path_dev: Path,
) -> None:
    shutil.copytree(tmodel_input_folder / "dflow-fm", tmp_path_dev)
    set_dfm_path(dflowfm_dll_devel)

    bmiwrapper = DfmWrapper(
        engine="dflowfm", configfile=tmodel_input_folder / "dflow-fm" / "FlowFM.mdu"
    )

    bmiwrapper.initialize()
    bmiwrapper.update()
    fluxes = bmiwrapper.get_1d_river_fluxes_ptr()
    assert fluxes is not None
    assert len(fluxes) == 20
    # @TODO
    # check if these  fluxes are supposed to be zero
    np.testing.assert_allclose(fluxes, 0)


def test_set_1d_river_fluxes(
    tmodel_input_folder: Path,
    dflowfm_dll_devel: Path,
    tmp_path_dev: Path,
) -> None:
    shutil.copytree(tmodel_input_folder / "dflow-fm", tmp_path_dev)
    set_dfm_path(dflowfm_dll_devel)

    bmiwrapper = DfmWrapper(engine="dflowfm", configfile=tmp_path_dev / "FlowFM.mdu")

    bmiwrapper.initialize()
    bmiwrapper.update()
    fluxes = bmiwrapper.get_1d_river_fluxes_ptr()
    assert fluxes is not None
    fluxes[:] = 20
    bmiwrapper.set_1d_river_fluxes(fluxes)
    new_fluxes = bmiwrapper.get_1d_river_fluxes_ptr()
    bmiwrapper.finalize()
    assert new_fluxes is not None
    np.testing.assert_allclose(fluxes, new_fluxes)


def test_get_node_numbers(
    tmodel_input_folder: Path,
    dflowfm_dll_devel: Path,
    tmp_path_dev: Path,
) -> None:
    shutil.copytree(tmodel_input_folder / "dflow-fm", tmp_path_dev)
    set_dfm_path(dflowfm_dll_devel)

    bmiwrapper = DfmWrapper(engine="dflowfm", configfile=tmp_path_dev / "FlowFM.mdu")

    bmiwrapper.initialize()
    bmiwrapper.update()

    nr_1d_nodes = bmiwrapper.get_number_1d_nodes()
    nr_2d_nodes = bmiwrapper.get_number_2d_nodes()
    nr_nodes = bmiwrapper.get_number_nodes()

    assert nr_1d_nodes == 20
    assert nr_2d_nodes == 110
    assert nr_nodes == 130
