import numpy as np
import pandas as pd
import xarray as xr
from numpy.typing import NDArray
from scipy.spatial import KDTree

from primod.typing import Bool, Float, Int


def _ensure_time_invariant_conductance(conductance: xr.DataArray) -> xr.DataArray:
    # Check that the conductance location does not change over time.
    # The imod_coupler has static weights: changing locations means having
    # to update the coupling weights over time as well.
    if "time" in conductance.dims:
        notnull = conductance.notnull()
        if (notnull.any("time") != notnull.all("time")).any():
            raise ValueError(
                "For imod_coupler, the active cells (defined by the conductance)"
                "in a river or drainage package must be constant over time."
            )
        return conductance.isel(time=0, drop=True)
    else:
        return conductance


def _find_coupled_cells(
    conductance: xr.DataArray,
    gridded_basin: xr.DataArray,
    basin_ids: pd.Series,
) -> tuple[NDArray[Int], NDArray[Bool]]:
    """
    Compare the location of conductance with the gridded basin.

    Either may have values where the other has NaN values.
    Only cells that have values in the conductance AND in the gridded
    basin should be coupled.
    """
    basin_id = xr.where(conductance.notnull(), gridded_basin, np.nan)  # type: ignore
    include = basin_id.notnull().to_numpy()
    basin_id_values = basin_id.to_numpy()[include].astype(int)
    # Ribasim internally sorts the basin, which determines the order of the
    # Ribasim state arrays.
    basin_index = np.searchsorted(basin_ids, basin_id_values)
    return basin_index, include


def _derive_boundary_index(
    conductance: xr.DataArray,
    include: NDArray[Bool],
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
    selection: NDArray[Int] = boundary_index_values[include.ravel()]
    return selection


def derive_passive_coupling(
    conductance: xr.DataArray,
    gridded_basin: xr.DataArray,
    basin_ids: pd.Series,
) -> pd.DataFrame:
    # Conductance is leading parameter to define location, for both river
    # and drainage.
    # Use xarray.where() to force the dimension order of conductance, rather than
    # using gridded_basin.where() (which prioritizes the gridded_basin dims)
    conductance = _ensure_time_invariant_conductance(conductance)
    basin_index, include = _find_coupled_cells(conductance, gridded_basin, basin_ids)
    boundary_index = _derive_boundary_index(conductance, include)
    return pd.DataFrame(
        data={"basin_index": basin_index, "bound_index": boundary_index}
    )


def _get_subgrid_xy(subgrid: pd.DataFrame) -> NDArray[Float]:
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
            "Subgrid data contains multiple values for meta_x or meta_y "
            f"for subgrid_id(s):\n   meta_x: {x_ids}\n   meta_y: {y_ids}"
        )

    x = grouped["meta_x"].first().to_numpy()
    y = grouped["meta_y"].first().to_numpy()
    return np.column_stack((x, y))


def _get_conductance_xy(
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
    conductance_xy: NDArray[Float] = xy[include2d]
    return conductance_xy


def _find_nearest_subgrid_elements(
    subgrid_xy: NDArray[Float],
    conductance_xy: NDArray[Float],
) -> NDArray[Int]:
    """Find the nearest subgrid element using a KD Tree."""
    kdtree = KDTree(subgrid_xy)
    # FUTURE: maybe do something with the distances returned by query?
    indices: NDArray[Int] = kdtree.query(conductance_xy)[1]
    return indices


def derive_active_coupling(
    conductance: xr.DataArray,
    gridded_basin: xr.DataArray,
    basin_ids: pd.Series,
    subgrid_df: pd.DataFrame,
) -> pd.DataFrame:
    # Conductance is leading parameter to define location, for both river
    # and drainage.
    # Use xarray.where() to force the dimension order of conductance, rather than
    # using gridded_basin.where() (which prioritizes the gridded_basin dims)
    conductance = _ensure_time_invariant_conductance(conductance)
    basin_index, include = _find_coupled_cells(conductance, gridded_basin, basin_ids)
    boundary_index = _derive_boundary_index(conductance, include)
    # Match the cells to the subgrid based on xy location.
    subgrid_xy = _get_subgrid_xy(subgrid_df)
    conductance_xy = _get_conductance_xy(conductance, include)
    subgrid_index = _find_nearest_subgrid_elements(subgrid_xy, conductance_xy)
    return pd.DataFrame(
        data={
            "basin_index": basin_index,
            "bound_index": boundary_index,
            "subgrid_index": subgrid_index,
        }
    )
