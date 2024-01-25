import numpy as np
import pandas as pd
import pytest
import xarray as xr
from primod.ribamod import exchange_creator as exc


def conductance():
    # Setup
    data = np.full((3, 4, 5), np.nan)
    data[0, 0, 0] = 1.0
    data[1, 1, 1] = 2.0
    data[2, 2, 2] = 3.0
    coords = {
        "x": [0.5, 1.5, 2.5, 3.5, 4.5],
        "y": [13.5, 12.5, 11.5, 10.5],
        "layer": [1, 2, 3],
    }
    dims = ("layer", "y", "x")
    return xr.DataArray(data=data, coords=coords, dims=dims)


def test_check_conductance():
    da = conductance()

    # Test
    actual = exc._check_conductance(da)
    assert actual is da

    # Now add time
    time_da = xr.DataArray([1.0, 1.0, 1.0], coords={"time": [0, 1, 2]}) * da
    actual = exc._check_conductance(time_da)
    assert actual.dims == ("layer", "y", "x")
    assert "time" not in actual.coords

    # Now move one entry in the second time to another place.
    time_da[1, 1, 1, 1] = np.nan
    time_da[1, 0, 0, 0] = 2.0
    with pytest.raises(ValueError, match="For imod_coupler, the active cells"):
        exc._check_conductance(time_da)


class TestFindCoupledCells:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.conductance = conductance()
        self.gridded_basin = xr.full_like(
            self.conductance.isel(layer=0, drop=True), np.nan
        )
        self.basin_ids = pd.Series([1, 3, 7, 11])

    def test_find_coupled_cells__all(self):
        da = xr.ones_like(self.conductance)
        gridded_basin = xr.full_like(self.gridded_basin, 3)
        basin_index, include = exc._find_coupled_cells(
            da, gridded_basin, self.basin_ids
        )

        # All cells are included
        assert basin_index.size == np.prod(da.shape)
        assert include.ndim == 3
        assert np.issubdtype(include.dtype, np.bool_)
        assert np.issubdtype(basin_index.dtype, np.integer)
        assert include.all()
        # All cells are located in the second basin.
        assert (basin_index == 1).all()

    def test_find_coupled_cells__some_basin(self):
        da = xr.ones_like(self.conductance)
        gridded_basin = xr.full_like(self.gridded_basin, 3)
        gridded_basin[..., 2:] = np.nan
        basin_index, include = exc._find_coupled_cells(
            da, gridded_basin, self.basin_ids
        )

        # Only the first two columns are included
        assert basin_index.size == (3 * 4 * 2)
        # All cells are located in the second basin.
        assert (basin_index == 1).all()
        # Check entries per layer
        assert include[..., :2].all()
        assert (~include[..., 2:]).all()

    def test_find_coupled_cells__some_conductance(self):
        da = xr.ones_like(self.conductance)
        gridded_basin = xr.full_like(self.gridded_basin, 3)
        da[..., 2:] = np.nan
        basin_index, include = exc._find_coupled_cells(
            da, gridded_basin, self.basin_ids
        )

        # Only the first two columns are included
        assert basin_index.size == (3 * 4 * 2)
        # All cells are located in the second basin.
        assert (basin_index == 1).all()
        # Check entries per layer
        assert include[..., :2].all()
        assert (~include[..., 2:]).all()

    def test_find_coupled_cells__multiple_basins(self):
        da = xr.ones_like(self.conductance)
        da[1:, ...] = np.nan
        gridded_basin = xr.full_like(self.gridded_basin, 3)
        gridded_basin[..., 2:] = 11
        basin_index, include = exc._find_coupled_cells(
            da, gridded_basin, self.basin_ids
        )

        assert np.array_equal(
            basin_index, [1, 1, 3, 3, 3, 1, 1, 3, 3, 3, 1, 1, 3, 3, 3, 1, 1, 3, 3, 3]
        )
        assert include[0, ...].all()
        assert (~include[1:, ...]).all()

    def test_find_coupled_cells(self):
        da = conductance()
        gridded_basin = xr.full_like(self.gridded_basin, 3)
        gridded_basin[:, 1] = 7
        gridded_basin[:, 2] = 11
        basin_index, _ = exc._find_coupled_cells(da, gridded_basin, self.basin_ids)
        assert np.array_equal(basin_index, [1, 2, 3])


def test_derive_boundary_index():
    da = conductance()
    include = da.notnull().to_numpy()
    boundary_id = exc._derive_boundary_index(da, include)
    assert np.array_equal(boundary_id, [0, 1, 2])

    da = xr.ones_like(conductance())
    boundary_id = exc._derive_boundary_index(da, include)
    assert np.array_equal(boundary_id, [0, 26, 52])


def test_derive_passive_coupling():
    da = conductance()
    gridded_basin = xr.full_like(da.isel(layer=0, drop=True), 7)
    basin_ids = pd.Series([1, 3, 7, 11])

    table = exc.derive_passive_coupling(da, gridded_basin, basin_ids)
    assert isinstance(table, pd.DataFrame)
    assert table.shape == (3, 2)
    pd.testing.assert_frame_equal(
        table,
        pd.DataFrame(data={"basin_index": [2, 2, 2], "bound_index": [0, 1, 2]}),
        check_dtype=False,  # int32 versus int64 ...
    )


def test_get_subgrid_xy():
    df = pd.DataFrame()
    with pytest.raises(ValueError, match='The columns "meta_x"'):
        exc._get_subgrid_xy(df)

    df = pd.DataFrame(
        data={
            "subgrid_id": [1, 1, 2, 2],
            "meta_x": [1.0, 1.0, 2.0, 3.0],
            "meta_y": [1.0, 1.0, 3.0, 2.0],
        }
    )
    with pytest.raises(ValueError, match="Subgrid data contains multiple"):
        exc._get_subgrid_xy(df)

    df = pd.DataFrame(
        data={
            "subgrid_id": [1, 1, 2, 2],
            "meta_x": [1.0, 1.0, 2.0, 2.0],
            "meta_y": [1.0, 1.0, 2.0, 2.0],
        }
    )
    xy = exc._get_subgrid_xy(df)
    assert np.allclose(
        xy,
        [
            [1.0, 1.0],
            [2.0, 2.0],
        ],
    )


def test_get_conductance_xy():
    da = conductance()
    include = da.notnull().to_numpy()
    xy = exc._get_conductance_xy(da, include)

    assert np.allclose(
        xy,
        [0.5, 13.5],
        [1.5, 12.5],
        [2.5, 11.5],
    )


def test_find_nearest_subgrid_elements():
    conductance_xy = np.array(
        [
            [0.5, 13.5],
            [1.5, 12.5],
            [2.5, 11.5],
        ]
    )
    subgrid_xy = np.array(
        [
            [-1.0, 12.0],
            [2.25, 11.75],
            [0.75, 13.2],
            [1.75, 12.5],
            [3.0, 12.0],
        ]
    )
    indices = exc._find_nearest_subgrid_elements(subgrid_xy, conductance_xy)

    assert np.array_equal(indices, [2, 3, 1])


def test_derive_active_coupling():
    da = conductance()
    gridded_basin = xr.full_like(da.isel(layer=0, drop=True), 7)
    basin_ids = pd.Series([1, 3, 7, 11])
    subgrid_df = pd.DataFrame(
        data={
            "subgrid_id": [0, 1, 2, 3, 4],
            "meta_x": [-1.0, 2.25, 0.75, 1.75, 3.0],
            "meta_y": [12.0, 11.75, 13.2, 12.5, 12.0],
        }
    )

    table = exc.derive_active_coupling(da, gridded_basin, basin_ids, subgrid_df)
    assert isinstance(table, pd.DataFrame)
    assert table.shape == (3, 3)
    pd.testing.assert_frame_equal(
        table,
        pd.DataFrame(
            data={
                "basin_index": [2, 2, 2],
                "bound_index": [0, 1, 2],
                "subgrid_index": [2, 3, 1],
            }
        ),
        check_dtype=False,  # int32 versus int64 ...
    )
