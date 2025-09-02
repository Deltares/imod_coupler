import shutil
from pathlib import Path

import pytest
from test_modstrip import fill_para_sim_template

from imod_coupler.kernelwrappers.msw_wrapper import MswWrapper


@pytest.mark.skip("metaswap can't be initialized and finalized more than once")
def test_msw_wrapper_can_be_initialized_and_finalized_multiple_times(
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    tmp_path_dev: Path,
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
