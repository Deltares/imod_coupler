import subprocess
from pathlib import Path

import imod
import numpy as np
import pandas as pd
import pytest
from numpy.testing import assert_allclose
from primod.ribamod import RibaMod
from pytest_cases import parametrize_with_cases


@pytest.mark.xdist_group(name="ribasim")
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
    Test if coupled ribamod models run with the iMOD Coupler development version.
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


@pytest.mark.xdist_group(name="ribasim")
@parametrize_with_cases("ribamod_model", glob="bucket_model")
def test_ribamod_bucket(
    tmp_path_dev: Path,
    ribamod_model: RibaMod,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    imod_coupler_exec_devel: Path,
) -> None:
    """
    Test if the bucket model works as expected
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
        tmp_path_dev / ribamod_model._ribasim_model_dir / "results" / "basin.arrow"
    )

    # There should be only a single node in the model
    assert (basin_df["node_id"] == 1).all()

    final_storage = basin_df.sort_values("time", ascending=False)["storage"].iloc[0]

    # Assert that the basin nearly empties
    assert final_storage < 60


@pytest.mark.xdist_group(name="ribasim")
@parametrize_with_cases("ribamod_model", glob="backwater_model")
def test_ribamod_backwater(
    tmp_path_dev: Path,
    ribamod_model: RibaMod,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    imod_coupler_exec_devel: Path,
) -> None:
    """
    Test if the backwater model works as expected
    """
    ribamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        ribasim_dll=ribasim_dll_devel,
        ribasim_dll_dependency=ribasim_dll_dep_dir_devel,
    )

    subprocess.run(
        [imod_coupler_exec_devel, tmp_path_dev / ribamod_model._toml_name],
        check=True,
    )

    # Read Ribasim output
    basin_df = pd.read_feather(
        tmp_path_dev / ribamod_model._ribasim_model_dir / "results" / "basin.arrow"
    )
    flow_df = pd.read_feather(
        tmp_path_dev / ribamod_model._ribasim_model_dir / "results" / "flow.arrow"
    )
    # Read MODFLOW 6 output
    head = imod.mf6.open_hds(
        tmp_path_dev / ribamod_model._modflow6_model_dir / "GWF_1" / "GWF_1.hds",
        tmp_path_dev / ribamod_model._modflow6_model_dir / "GWF_1" / "dis.dis.grb",
    ).compute()

    budgets = imod.mf6.open_cbc(
        tmp_path_dev / ribamod_model._modflow6_model_dir / "GWF_1" / "GWF_1.cbc",
        tmp_path_dev / ribamod_model._modflow6_model_dir / "GWF_1" / "dis.dis.grb",
    )

    final_level = basin_df[basin_df["time"] == "2029-12-01"]["level"]

    # Assert that the final level is a mototonically decreasing curve.
    assert (np.diff(final_level) < 0).all()
    # The head should follow the same pattern.
    assert (head.isel(layer=0, time=-1).diff("x") < 0.0).all()

    drn = budgets["drn-1"].compute()
    riv = budgets["riv-1"].compute()
    # At the last time step, the drain and the river should have equal water
    # balance terms since they have the same conductance and the river_stage =
    # drainage_elevation.
    assert_allclose(drn.isel(time=-1), riv.isel(time=-1))

    # Get the last flow between the edges
    final_flow = flow_df[flow_df["time"] == "2029-12-01"]
    # Check's what lost and gained in the basins
    network = ribamod_model.ribasim_model.network
    basin_ids = network.node.df.index[network.node.df["type"] == "Basin"]
    ribasim_budget = (
        final_flow.loc[
            final_flow["from_node_id"].isin(basin_ids)
            & final_flow["to_node_id"].isin(basin_ids)
        ]["flow"]
        * 86_400.0
    ).to_numpy()
    modflow_budget = (drn + riv).isel(time=-1).sel(y=0).to_numpy()
    budget_diff = ribasim_budget + modflow_budget
    assert (np.abs(budget_diff) < 1.0e-6).all()


@pytest.mark.xdist_group(name="ribasim")
@parametrize_with_cases("ribamod_model", glob="two_basin_model")
def test_ribamod_two_basin(
    tmp_path_dev: Path,
    ribamod_model: RibaMod,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    imod_coupler_exec_devel: Path,
) -> None:
    """
    Test if the two basin model works as expected
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

    # Read Ribasim output
    basin_df = pd.read_feather(
        tmp_path_dev / ribamod_model._ribasim_model_dir / "results" / "basin.arrow"
    )
    flow_df = pd.read_feather(
        tmp_path_dev / ribamod_model._ribasim_model_dir / "results" / "flow.arrow"
    )
    # Read MODFLOW 6 output
    head = imod.mf6.open_hds(
        tmp_path_dev / ribamod_model._modflow6_model_dir / "GWF_1" / "GWF_1.hds",
        tmp_path_dev / ribamod_model._modflow6_model_dir / "GWF_1" / "dis.dis.grb",
    ).compute()

    # FUTURE: think of better tests?
    # The head should only decrease, going from left to right.
    assert bool(head.isel(time=-1, layer=0).diff("x").all())

    # Water is flowing from basin1 through the ground to basin2.
    level1, level2 = basin_df.loc[basin_df["time"] == "2030-01-01"]["level"]
    assert level1 > level2

    # Flow in the edges is always to the right.
    assert (flow_df["flow"].loc[flow_df["edge_id"].notna()] >= 0).all()


@pytest.mark.xdist_group(name="ribasim")
@parametrize_with_cases("ribamod_model", glob="partial_two_basin_model")
def test_ribamod_partial_two_basin(
    tmp_path_dev: Path,
    ribamod_model: RibaMod,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    imod_coupler_exec_devel: Path,
) -> None:
    """
    Test if the partial two basin model works as expected
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

    # Read Ribasim output
    basin_df = pd.read_feather(
        tmp_path_dev / ribamod_model._ribasim_model_dir / "results" / "basin.arrow"
    )
    flow_df = pd.read_feather(
        tmp_path_dev / ribamod_model._ribasim_model_dir / "results" / "flow.arrow"
    )
    # Read MODFLOW 6 output
    head = imod.mf6.open_hds(
        tmp_path_dev / ribamod_model._modflow6_model_dir / "GWF_1" / "GWF_1.hds",
        tmp_path_dev / ribamod_model._modflow6_model_dir / "GWF_1" / "dis.dis.grb",
    ).compute()

    # The top and bottom rows have non coupled river boundaries with a stage of
    # 0.5 m and a large conductance.
    # The resulting head values should be approximately 0.5 m.
    assert (abs(head.isel(time=-1, y=0) - 0.5) < 0.01).all()
    assert (abs(head.isel(time=-1, y=-1) - 0.5) < 0.01).all()

    # The center head should be close to the left basin level.
    # Basin level is quite high due to large inflow: about 273 m...
    last_level_left = basin_df.loc[basin_df["node_id"] == 2, "level"].iloc[-1]
    center_head = head.isel(time=-1).sel(y=0, method="nearest")
    stage_head_diff = last_level_left - center_head
    assert (stage_head_diff < 2.0).all()

    # The rightmost basin is not coupled, nor connected with the left basin.
    # It should only empty with tiny flows.
    # If it is connected, it would have much larger flow due to groundwater
    # draining.
    flow_to_terminal = flow_df.loc[
        (flow_df["from_node_id"] == 4) & (flow_df["to_node_id"] == 5)
    ]["flow"]
    assert flow_to_terminal.iloc[-1] < 1.0e-9


@pytest.mark.xdist_group(name="ribasim")
@parametrize_with_cases("ribamod_model", glob="uncoupled_two_basin_model")
def test_ribamod_uncoupled_two_basin(
    tmp_path_dev: Path,
    ribamod_model: RibaMod,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    imod_coupler_exec_devel: Path,
) -> None:
    """
    Test if the partial two basin model works as expected if there's no spatial
    overlap between the RibaMod and Modflow6 model.
    """
    ribamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        ribasim_dll=ribasim_dll_devel,
        ribasim_dll_dependency=ribasim_dll_dep_dir_devel,
    )

    # Should run without exceptions.
    subprocess.run(
        [imod_coupler_exec_devel, tmp_path_dev / ribamod_model._toml_name], check=True
    )
