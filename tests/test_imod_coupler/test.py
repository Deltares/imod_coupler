from pathlib import Path

import imod
import numpy as np
import pandas as pd
import xarray as xr

# from imod_coupler.__main__ import run_coupler

basin_df = pd.read_feather(
    r"c:\Users\kok_hk\AppData\Local\Temp\pytest-of-kok_hk\pytest-381\test_ribametamod_two_basin_use0\develop\ribasim\results\allocation_flow.arrow"
)
basin_df.to_csv(
    r"c:\Users\kok_hk\AppData\Local\Temp\pytest-of-kok_hk\pytest-381\test_ribametamod_two_basin_use0\develop\ribasim\results\allocation_flow.csv"
)

pass


def read_heads(headfile, grbfile):
    heads = imod.mf6.open_hds(headfile, grbfile, False)
    starttime = pd.to_datetime("2000/01/01")
    timedelta = pd.to_timedelta(heads["time"] - 1.0, "D")
    return heads.assign_coords(time=starttime + timedelta)


toml = Path(
    r"c:\Users\kok_hk\AppData\Local\Temp\pytest-of-kok_hk\pytest-300\test_ribametamod_two_basin_use0\develop\imod_coupler.toml"
)


# run_coupler(toml)
headfile = toml.parent / "modflow6" / "GWF_1" / "GWF_1.hds"
grbfile = toml.parent / "modflow6" / "GWF_1" / "dis.dis.grb"
# test = xr.open_dataset(toml.parent / "exchange_logging" / "exchange_demand_riv-1.nc")
heads = read_heads(headfile, grbfile)
imod.idf.save("heads.idf", heads)

pass
target = imod.idf.open(
    r"c:\Users\kok_hk\AppData\Local\Temp\pytest-of-kok_hk\pytest-96\test_ribametamod_bucket_bucket0\develop\metaswap\bdgqrun\bdgqrun_20221231_L1.IDF"
).isel(time=0, layer=0, drop=True)
ncol = target.x.size
nrow = target.y.size

mask_ar = np.zeros(ncol * nrow)
# mask_ar[coupled_indices - 1] = 1
mask = xr.DataArray(
    data=mask_ar.reshape(nrow, ncol), coords=target.coords, dims=target.dims
)


imod.idf.save("mask.idf", mask)


pass

toml = Path(
    r"c:\Users\kok_hk\AppData\Local\Temp\pytest-of-kok_hk\pytest-54\test_ribametamod_bucket_bucket0\develop\imod_coupler.toml"
)
# run_coupler(toml)


def read_heads(headfile, grbfile):
    heads = imod.mf6.open_hds(headfile, grbfile, False)
    starttime = pd.to_datetime("2000/01/01")
    timedelta = pd.to_timedelta(heads["time"] - 1.0, "D")
    return heads.assign_coords(time=starttime + timedelta)


# headfile = toml.parent / "modflow6" / "GWF_1" / "GWF_1.hds"
# grbfile = toml.parent / "modflow6" / "GWF_1" / "dis.dis.grb"
#
# heads = read_heads(headfile, grbfile)
# imod.idf.save(toml.parent / "heads.idf", heads)

imod.idf.open(r"")


pass
