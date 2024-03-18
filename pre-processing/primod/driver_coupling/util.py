import geopandas as gpd
import numpy as np
import pandas as pd
import ribasim
import xarray as xr
from imod.mf6 import Modflow6Simulation
from numpy.typing import NDArray

from primod.typing import Int


def _validate_node_ids(
    ribasim_model: ribasim.Model, definition: gpd.GeoDataFrame
) -> pd.Series:
    # Validate
    if "node_id" not in definition.columns:
        raise ValueError(
            'Definition must contain "node_id" column.'
            f"Columns in dataframe: {definition.columns}"
        )
    assert ribasim_model.basin.profile.df is not None

    basin_ids: NDArray[Int] = np.unique(ribasim_model.basin.profile.df["node_id"])
    missing = ~np.isin(definition["node_id"], basin_ids)
    if missing.any():
        missing_nodes = definition["node_id"].to_numpy()[missing]
        raise ValueError(
            "The node IDs of these nodes in definition do not "
            f"occur in the Ribasim model: {missing_nodes}"
        )
    return basin_ids


def _validate_time_window(
    ribasim_model: ribasim.Model,
    mf6_simulation: Modflow6Simulation,
) -> None:
    def to_timestamp(xr_time: xr.DataArray) -> pd.Timestamp:
        return pd.Timestamp(xr_time.to_numpy().item())

    mf6_timedis = mf6_simulation["time_discretization"].dataset
    mf6_start = to_timestamp(mf6_timedis["time"].isel(time=0)).to_pydatetime()
    time_delta = pd.to_timedelta(
        mf6_timedis["timestep_duration"].isel(time=-1).item(), unit="days"
    )
    mf6_end = (
        to_timestamp(mf6_timedis["time"].isel(time=-1)) + time_delta
    ).to_pydatetime()

    ribasim_start = ribasim_model.starttime
    ribasim_end = ribasim_model.endtime
    if ribasim_start != mf6_start or ribasim_end != mf6_end:
        raise ValueError(
            "Ribasim simulation time window does not match MODFLOW6.\n"
            f"Ribasim: {ribasim_start} to {ribasim_end}\n"
            f"MODFLOW6: {mf6_start} to {mf6_end}\n"
        )
    return
