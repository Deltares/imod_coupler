import geopandas as gpd
import numpy as np
import pandas as pd
import ribasim
import xarray as xr
from imod.mf6 import Drainage, GroundwaterFlowModel, Modflow6Simulation, River
from numpy.typing import NDArray

from primod.typing import Int


def _get_gwf_modelnames(mf6_simulation: Modflow6Simulation) -> list[str]:
    """
    Get names of gwf models in mf6 simulation
    """
    return [
        key
        for key, value in mf6_simulation.items()
        if isinstance(value, GroundwaterFlowModel)
    ]


def _validate_node_ids(
    dataframe: pd.DataFrame, definition: gpd.GeoDataFrame
) -> pd.Series:
    # Validate
    if "node_id" not in definition.columns:
        raise ValueError(
            'Definition must contain "node_id" column.'
            f"Columns in dataframe: {definition.columns}"
        )

    basin_ids: NDArray[Int] = np.unique(dataframe["node_id"])
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


def _validate_keys(
    gwf_model: GroundwaterFlowModel,
    active_keys: list[str],
    passive_keys: list[str],
    expected_type: River | Drainage,
) -> None:
    active_keys_set = set(active_keys)
    passive_keys_set = set(passive_keys)
    intersection = active_keys_set.intersection(passive_keys_set)
    if intersection:
        raise ValueError(f"active and passive keys share members: {intersection}")
    present = [k for k, v in gwf_model.items() if isinstance(v, expected_type)]
    missing = (active_keys_set | passive_keys_set).difference(present)
    if missing:
        raise ValueError(
            f"keys with expected type {expected_type.__name__} are not "
            f"present in the model: {missing}"
        )


def _nullify_ribasim_exchange_input(
    ribasim_component: ribasim.Basin | ribasim.UserDemand,
    coupled_basin_node_ids: NDArray[Int],
    columns: list[str],
) -> None:
    """
    Set the input forcing to NoData for drainage and infiltration.

    Ribasim will otherwise overwrite the values set by the coupler.
    """

    # FUTURE: in coupling to MetaSWAP, the runoff should be set nodata as well.
    def _nullify(df: pd.DataFrame) -> None:
        """E.g. set drainage, infiltration, runoff columns to nodata if present in df"""
        if df is not None:
            columns_present = list(set(columns).intersection(df.columns))
            if len(columns_present) > 0:
                df.loc[df["node_id"].isin(coupled_basin_node_ids), columns_present] = (
                    np.nan
                )
        return

    _nullify(ribasim_component.static.df)
    _nullify(ribasim_component.time.df)
    return
