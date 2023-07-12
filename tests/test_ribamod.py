import subprocess
from pathlib import Path

import pandas as pd
from imod.couplers.ribamod import RibaMod
from pytest_cases import parametrize_with_cases


@parametrize_with_cases("ribamod_model")
def test_ribamod_develop(
    tmp_path_dev: Path,
    ribamod_model: RibaMod,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    imod_coupler_exec_devel: Path,
) -> None:
    """
    Test if coupled models run with the iMOD Coupler development version.
    """
    ribamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        ribasim_dll=ribasim_dll_devel,
        ribasim_dll_dependency=ribasim_dll_dep_dir_devel,
    )

    subprocess.run(
        [imod_coupler_exec_devel, tmp_path_dev / ribamod_model._toml_name], check=True
    )

    basin_df = pd.read_feather(
        tmp_path_dev / ribamod_model._ribasim_model_dir / "output" / "basin.arrow"
    )

    # There should be only a single node in the model
    assert (basin_df["node_id"] == 1).all()

    final_storage = basin_df.sort_values("time", ascending=False)["storage"].iloc[0]

    # Assert that the basin nearly empties
    assert final_storage < 60
