import numpy as np
import pandas as pd
import xarray as xr
from numpy.typing import NDArray
from scipy.spatial import KDTree

Int = np.int_
Float = np.float_
Bool = np.bool_


def check_conductance(conductance: xr.DataArray) -> xr.DataArray:
    # FUTURE: check that the conductance location does not change over time.
    # The imod_coupler has static weights: changing locations means having
    # to update the coupling weights over time as well.
    if "time" in conductance.dims:
        return conductance.isel(time=0, drop=True)
    else:
        return conductance


def find_coupled_cells(
    conductance: xr.DataArray,
    gridded_basin: xr.DataArray,
    basin_ids: "pd.Series[int]",
) -> tuple[NDArray[Int], NDArray[Bool]]:
    """
    Compare the location of conductance with the gridded basin.

    Either may have values where the other has NaN values.
    Only cells that have values in the conductance AND in the gridded
    basin should be coupled.
    """
    # Conductance is leading parameter to define location, for both river
    # and drainage.
    # FUTURE: check for time dimension? Also order and inclusion of layer
    # in conductance.
    # Use xarray where to force the dimension order of conductance.
    conductance = check_conductance(conductance)
    basin_id = xr.where(conductance.notnull(), gridded_basin, np.nan)  # type: ignore
    include = basin_id.notnull().to_numpy()
    basin_id_values = basin_id.to_numpy()[include].astype(int)
    # Ribasim internally sorts the basin, which determines the order of the
    # Ribasim state arrays.
    basin_index = np.searchsorted(basin_ids, basin_id_values)
    return basin_index, include


def derive_boundary_index(
    conductance: xr.DataArray,
    include: np.ndarray,
) -> NDArray[Int]:
    """
    Create the numbering for each boundary cell.

    E.g. a 3 by 3 conductance grid:
    [
        [nan, 1.0, np.nan],
        [nan, 1.0, np.nan],
        [2.0, 1.0, 4.0],
    ]

    Will have essentially the boundary_index_values:

    [
        [None, 0, None],
        [None, 1, None],
        [2, 3, 4],
    ]

    However, the gridded_basin might look like:

    [
        [nan, 1, nan],
        [nan, 1, nan],
        [nan, 2, 2],
    ]

    I.e. the bottom-left cell is not included in the basin definition.

    Then, the desired return values are: [0, 1, 3, 4]

    This implements this in a vectorized manner.
    """
    # The first value found by cumsum will have a 1, while the coupler is 0-indexed.
    boundary_index_values = np.cumsum(conductance.notnull().to_numpy().ravel()) - 1
    selection = boundary_index_values[include.ravel()]
    return selection


def derive_passive_coupling(
    conductance: xr.DataArray,
    gridded_basin: xr.DataArray,
    basin_ids: "pd.Series[int]",
) -> pd.DataFrame:
    basin_index, include = find_coupled_cells(conductance, gridded_basin, basin_ids)
    boundary_index = derive_boundary_index(conductance, include)
    return pd.DataFrame(
        data={"basin_index": basin_index, "bound_index": boundary_index}
    )


def get_subgrid_xy(subgrid: pd.DataFrame) -> np.ndarray:
    # Check whether columns (optional to Ribasim) are present.
    if "meta_x" not in subgrid or "meta_y" not in subgrid:
        raise ValueError(
            'The columns "meta_x" and "meta_y" are required in the '
            "ribasim.Model.basin.subgrid dataframe for actively coupled river "
            f"and drainage packages. Found columns: {subgrid.columns}"
        )

    # Check x and y coordinates for uniqueness
    grouped = subgrid.groupby("subgrid_id")
    multiple_x = grouped["meta_x"].nunique().ne(1)
    multiple_y = grouped["meta_y"].nunique().ne(1)
    if multiple_x.any() or multiple_y.any():
        x_ids = multiple_x.index[multiple_x].to_numpy()
        y_ids = multiple_y.index[multiple_y].to_numpy()
        raise ValueError(
            "subgrid data contains multiple values for meta_x or meta_y "
            f"for subgrid_id(s):\n   meta_x: {x_ids}\n   meta_y: {y_ids}"
        )

    x = grouped["meta_x"].first().to_numpy()
    y = grouped["meta_y"].first().to_numpy()
    return np.column_stack((x, y))


def get_conductance_xy(
    conductance: xr.DataArray, include: NDArray[Bool]
) -> NDArray[Float]:
    # Include incorporates the layer dimension
    # We don't want to replicate x and y for each layer.
    # Instead, compute the indices into the x and y array for a single layer.
    x = conductance["x"].to_numpy()
    y = conductance["y"].to_numpy()
    n_per_layer = y.size * x.size
    include2d = np.flatnonzero(include) % n_per_layer
    yy, xx = np.meshgrid(y, x, indexing="ij")
    xy = np.column_stack((xx.ravel(), yy.ravel()))
    return xy[include2d]


def find_nearest_subgrid_elements(
    subgrid_xy: np.ndarray, conductance_xy: np.ndarray
) -> NDArray[Int]:
    """Find the nearest subgrid element using a KD Tree."""
    kdtree = KDTree(subgrid_xy)
    # FUTURE: maybe do something with the distances returned by query?
    _, indices = kdtree.query(conductance_xy)
    return indices


def derive_active_coupling(
    gridded_basin: xr.DataArray,
    basin_ids: "pd.Series[int]",
    conductance: xr.DataArray,
    subgrid_df: pd.DataFrame,
) -> pd.DataFrame:
    basin_index, include = find_coupled_cells(conductance, gridded_basin, basin_ids)
    boundary_index = derive_boundary_index(conductance, include)
    # Match the cells to the subgrid based on xy location.
    subgrid_xy = get_subgrid_xy(subgrid_df)
    conductance_xy = get_conductance_xy(conductance, include)
    subgrid_index = find_nearest_subgrid_elements(subgrid_xy, conductance_xy)
    return pd.DataFrame(
        data={
            "basin_index": basin_index,
            "bound_index": boundary_index,
            "subgrid_index": subgrid_index,
        }
    )
