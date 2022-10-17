import numpy as np
import pandas as pd
import xarray as xr


def create_discretization():

    shape = nlay, nrow, ncol = 2, 2, 5

    dx = 1
    dy = -1

    xmin = 0.0
    xmax = dx * ncol
    ymin = 0.0
    ymax = abs(dy) * nrow
    dims = ("layer", "y", "x")

    layer = np.arange(1, nlay + 1)
    y = np.arange(ymax, ymin, dy) + 0.5 * dy
    x = np.arange(xmin, xmax, dx) + 0.5 * dx
    coords = {"layer": layer, "y": y, "x": x, "dy": dy, "dx": dx}

    idomain = xr.DataArray(np.ones(shape, dtype=np.int32), coords=coords, dims=dims)

    bottom = xr.full_like(idomain, np.nan, dtype=np.floating)
    bottom.values[0, :, :] = -1
    bottom.values[1, :, :] = -2
    top = 0.0
    times = pd.date_range(start="1/1/1971", end="8/1/1971", freq="D")
    return idomain, top, bottom, times
