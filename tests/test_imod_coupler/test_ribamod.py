from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple

import imod
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from primod.ribamod import RibaMod
from pytest_cases import parametrize_with_cases


class Results(NamedTuple):
    basin_df: pd.DataFrame
    flow_df: pd.DataFrame
    head: xr.DataArray
    budgets: dict[str, xr.DataArray]


def write_run_read(
    tmp_path: Path,
    ribamod_model: RibaMod,
    modflow_dll: Path,
    ribasim_dll: Path,
    ribasim_dll_dep_dir: Path,
    run_coupler_function: Callable[[Path], None],
) -> Results:
    """
    Write the model, run it, read and return the results.
    """
    ribamod_model.write(
        tmp_path,
        modflow6_dll=modflow_dll,
        ribasim_dll=ribasim_dll,
        ribasim_dll_dependency=ribasim_dll_dep_dir,
    )

    run_coupler_function(tmp_path / ribamod_model._toml_name)

    # Read Ribasim output
    basin_df = pd.read_feather(
        tmp_path / ribamod_model._ribasim_model_dir / "results" / "basin.arrow"
    )
    if not ribamod_model.ribasim_model.edge.df.empty:
        flow_df = pd.read_feather(
            tmp_path / ribamod_model._ribasim_model_dir / "results" / "flow.arrow"
        )
    else:
        flow_df = pd.DataFrame()

    # Read MODFLOW 6 output
    head = imod.mf6.open_hds(
        tmp_path / ribamod_model._modflow6_model_dir / "GWF_1" / "GWF_1.hds",
        tmp_path / ribamod_model._modflow6_model_dir / "GWF_1" / "dis.dis.grb",
    ).compute()

    budgets = imod.mf6.open_cbc(
        tmp_path / ribamod_model._modflow6_model_dir / "GWF_1" / "GWF_1.cbc",
        tmp_path / ribamod_model._modflow6_model_dir / "GWF_1" / "dis.dis.grb",
    )
    return Results(basin_df, flow_df, head, budgets)


@pytest.mark.xdist_group(name="ribasim")
@parametrize_with_cases("ribamod_model")
def test_ribamod_develop(
    tmp_path_dev: Path,
    ribamod_model: RibaMod,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    run_coupler_function: Callable[[Path], None],
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

    run_coupler_function(tmp_path_dev / ribamod_model._toml_name)


@pytest.mark.xdist_group(name="ribasim")
@parametrize_with_cases("ribamod_model", glob="bucket_model")
def test_ribamod_bucket(
    tmp_path_dev: Path,
    ribamod_model: RibaMod,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    run_coupler_function: Callable[[Path], None],
) -> None:
    """
    Test if the bucket model works as expected
    """
    results = write_run_read(
        tmp_path=tmp_path_dev,
        ribamod_model=ribamod_model,
        modflow_dll=modflow_dll_devel,
        ribasim_dll=ribasim_dll_devel,
        ribasim_dll_dep_dir=ribasim_dll_dep_dir_devel,
        run_coupler_function=run_coupler_function,
    )
    # There should be only a single node in the model
    assert (results.basin_df["node_id"] == 1).all()

    final_storage = results.basin_df.sort_values("time", ascending=False)[
        "storage"
    ].iloc[0]

    # Assert that the basin nearly empties
    assert final_storage < 60

    # Alter ribasim subgrid level to trigger an exception (minimum subgrid level above modflow bottom elevation)
    ribamod_model.ribasim_model.basin.subgrid.df.loc[0, "subgrid_level"] = 0.3
    with pytest.raises(
        ValueError,
    ):
        results = write_run_read(
            tmp_path=tmp_path_dev,
            ribamod_model=ribamod_model,
            modflow_dll=modflow_dll_devel,
            ribasim_dll=ribasim_dll_devel,
            ribasim_dll_dep_dir=ribasim_dll_dep_dir_devel,
            run_coupler_function=run_coupler_function,
        )


@pytest.mark.xdist_group(name="ribasim")
@parametrize_with_cases("ribamod_model", glob="backwater_model")
def test_ribamod_backwater(
    tmp_path_dev: Path,
    ribamod_model: RibaMod,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    run_coupler_function: Callable[[Path], None],
) -> None:
    """
    Test if the backwater model works as expected
    """
    results = write_run_read(
        tmp_path=tmp_path_dev,
        ribamod_model=ribamod_model,
        modflow_dll=modflow_dll_devel,
        ribasim_dll=ribasim_dll_devel,
        ribasim_dll_dep_dir=ribasim_dll_dep_dir_devel,
        run_coupler_function=run_coupler_function,
    )

    final_level = results.basin_df[results.basin_df["time"] == "2020-12-31"]["level"]

    # Assert that the final level is a mototonically decreasing curve.
    assert (np.diff(final_level) < 0).all()
    # The head should follow the same pattern.
    assert (results.head.isel(layer=0, time=-1).diff("x") < 0.0).all()

    drn = results.budgets["drn_drn-1"].isel(time=-1).compute()
    riv = results.budgets["riv_riv-1"].isel(time=-1).compute()

    # Get the last flow between the edges
    volume_balance = results.basin_df[results.basin_df["time"] == "2020-12-31"]
    # Check's what lost and gained in the basins
    ribasim_budget = (
        (volume_balance["infiltration"] - volume_balance["drainage"])[:-1] * 86_400.0
    ).to_numpy()
    # It seems that there is a match of integrated volumes shifted by half a timestep.
    # the integration of flux on the Ribasim side deserves a closer look
    modflow_budget = (drn + riv).sel(y=0).to_numpy()
    budget_diff = ribasim_budget - modflow_budget
    assert (np.abs(budget_diff) < 1.0e-4).all()


@pytest.mark.xdist_group(name="ribasim")
@parametrize_with_cases("ribamod_model", glob="two_basin_model")
def test_ribamod_two_basin(
    tmp_path_dev: Path,
    ribamod_model: RibaMod,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    run_coupler_function: Callable[[Path], None],
) -> None:
    """
    Test if the two basin model works as expected
    """
    results = write_run_read(
        tmp_path=tmp_path_dev,
        ribamod_model=ribamod_model,
        modflow_dll=modflow_dll_devel,
        ribasim_dll=ribasim_dll_devel,
        ribasim_dll_dep_dir=ribasim_dll_dep_dir_devel,
        run_coupler_function=run_coupler_function,
    )

    # FUTURE: think of better tests?
    # The head should only decrease, going from left to right.
    assert bool(results.head.isel(time=-1, layer=0).diff("x").all())

    # Water is flowing from basin1 through the ground to basin2.
    level1, level2 = results.basin_df.loc[results.basin_df["time"] == "2020-02-01"][
        "level"
    ]
    assert level1 > level2

    # Flow in the edges is always to the right.
    assert (
        results.flow_df["flow_rate"].loc[results.flow_df["link_id"].notna()] >= 0
    ).all()


@pytest.mark.xdist_group(name="ribasim")
@parametrize_with_cases("ribamod_model", glob="partial_two_basin_model")
def test_ribamod_partial_two_basin(
    tmp_path_dev: Path,
    ribamod_model: RibaMod,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    run_coupler_function: Callable[[Path], None],
) -> None:
    """
    Test if the partial two basin model works as expected
    """
    results = write_run_read(
        tmp_path=tmp_path_dev,
        ribamod_model=ribamod_model,
        modflow_dll=modflow_dll_devel,
        ribasim_dll=ribasim_dll_devel,
        ribasim_dll_dep_dir=ribasim_dll_dep_dir_devel,
        run_coupler_function=run_coupler_function,
    )

    # The top and bottom rows have non coupled river boundaries with a stage of
    # 0.5 m and a large conductance.
    # The resulting head values should be approximately 0.5 m.
    assert (abs(results.head.isel(time=-1, y=0) - 0.5) < 0.01).all()
    assert (abs(results.head.isel(time=-1, y=-1) - 0.5) < 0.01).all()

    # The center head should be close to the left basin level.
    # Basin level is quite high due to large inflow: about 273 m...
    last_level_left = results.basin_df.loc[
        results.basin_df["node_id"] == 2, "level"
    ].iloc[-1]
    center_head = results.head.isel(time=-1).sel(y=0, method="nearest")
    stage_head_diff = last_level_left - center_head
    assert (stage_head_diff < 2.0).all()

    # The rightmost basin is not coupled, nor connected with the left basin.
    # It should only empty with tiny flows.
    # If it is connected, it would have much larger flow due to groundwater
    # draining.
    flow_to_terminal = results.flow_df.loc[
        (results.flow_df["from_node_id"] == 4) & (results.flow_df["to_node_id"] == 5)
    ]["flow_rate"]
    assert flow_to_terminal.iloc[-1] < 1.0e-6
