import numpy as np
import pandas as pd
import xarray as xr
from imod.mf6.wel import LayeredWell
from numpy import float64, int_
from numpy.typing import NDArray


def grid_sizes() -> (
    tuple[
        list[float],
        list[float],
        NDArray[int_],
        float,
        float,
        NDArray[float64],
    ]
):
    x = [100.0, 200.0, 300.0, 400.0, 500.0]
    y = [300.0, 200.0, 100.0]
    dz = np.array([0.2, 10.0, 100.0])

    layer = np.arange(len(dz)) + 1
    dx = x[1] - x[0]
    dy = y[1] - y[0]

    return x, y, layer, dx, dy, dz


def get_times() -> pd.DatetimeIndex:
    freq = "D"
    return pd.date_range(start="1/1/1971", end="8/1/1971", freq=freq)


def create_wells(idomain: xr.DataArray, wel_layer: int | None = None) -> LayeredWell:
    """
    Create wells, deactivate inactive cells. This function wouldn't be necessary
    if iMOD Python had a package to specify wells based on grids.
    """

    if wel_layer is None:
        wel_layer = 3

    x = idomain.coords["x"].to_numpy()
    y = idomain.coords["y"].to_numpy()

    x_grid, y_grid = np.meshgrid(x, y)

    is_inactive = ~idomain.sel(layer=wel_layer).astype(bool)
    id_inactive = np.argwhere(is_inactive.values) + 1

    ix = np.ravel(x_grid)
    iy = np.ravel(y_grid)

    to_deactivate = np.full_like(ix, False, dtype=bool)
    for i in id_inactive:
        is_cell = (iy == i[0]) & (ix == i[1])
        to_deactivate = to_deactivate | is_cell

    ix_active = ix[~to_deactivate]
    iy_active = iy[~to_deactivate]

    rate = np.zeros(ix_active.shape)
    layer = np.full_like(ix_active, wel_layer, dtype=int)

    return LayeredWell(ix_active, iy_active, layer, rate)


def create_wells_max_layer(idomain: xr.DataArray) -> LayeredWell:
    """
    Create wells in deepest layer of MODFLOW 6 model
    """

    wel_layer = idomain.layer.max().item()
    return create_wells(idomain, wel_layer)
