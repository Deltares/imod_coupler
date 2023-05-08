import os
import shutil
from pathlib import Path

import pytest
from imod import mf6
from imod_coupler.kernelwrappers.mf6_wrapper import Mf6Wrapper
from imod_coupler.kernelwrappers.msw_wrapper import MswWrapper
from test_modstrip import fill_para_sim_template
from xmipy import XmiWrapper


def test_xmi_wrapper_can_be_initialized_and_finalized_multiple_times(
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
    mf6wrapper.finalize()
    mf6wrapper.initialize()
    mf6wrapper.finalize()


@pytest.mark.skip("metaswap can't be initialized and finalized more than once")
def test_msw_wrapper_can_be_initialized_and_finalized_multiple_times(
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    tmp_path_dev,
    tmodel_short_input_folder: Path,
    metaswap_lookup_table: Path,
) -> None:
    shutil.copytree(tmodel_short_input_folder, tmp_path_dev)
    msw = MswWrapper(
        metaswap_dll_devel,
        metaswap_dll_dep_dir_devel,
        tmp_path_dev / "MetaSWAP",
        False,
    )

    fill_para_sim_template(tmp_path_dev / "MetaSWAP", metaswap_lookup_table)
    msw.initialize()
    msw.finalize()
    msw.initialize()
    msw.finalize()
