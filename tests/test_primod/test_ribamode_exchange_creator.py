import pytest
import numpy as np
import xarray as xr

from primod.ribamod import exchange_creator as exc


def test_check_conductance():
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
    da = xr.DataArray(data=data, coords=coords, dims=dims)
    
    # Test
    actual = exc._check_conductance(da)
    assert actual is da
    
    # Now add time
    time_da = xr.DataArray([1.0, 1.0, 1.0], coords={"time": [0, 1, 2]}) * da
    actual = exc._check_conductance(time_da)
    assert actual.dims == ("layer", "y", "x")
    assert "time" not in actual.coords
    
    # Now remove one entry in the second time.
    time_da.values[1, 0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="For imod_coupler, the number of active cells"):
        exc._check_conductance(time_da)
