from pathlib import Path

import imod
import numpy as np
import pandas as pd
import xarray as xr

# from imod_coupler.__main__ import run_coupler


idomain = np.array([1, 1, np.nan, 1]).reshape(2, 2)

user_id = np.arange(idomain.size)[idomain.ravel() == 1]

user_selection = np.array([0, 2])


target = np.zeros_like(idomain).ravel()

target[user_id[user_selection]] = np.ones_like(user_selection)


pass


path = r"c:\Users\kok_hk\AppData\Local\Temp\pytest-of-kok_hk\pytest-96\test_ribametamod_bucket_bucket0\develop\exchanges\msw_ponding.tsv"
coupled_indices = pd.read_csv(path, delimiter="\t")["svat_index"].values

target = imod.idf.open(
    r"c:\Users\kok_hk\AppData\Local\Temp\pytest-of-kok_hk\pytest-96\test_ribametamod_bucket_bucket0\develop\metaswap\bdgqrun\bdgqrun_20221231_L1.IDF"
).isel(time=0, layer=0, drop=True)
ncol = target.x.size
nrow = target.y.size

mask_ar = np.zeros(ncol * nrow)
mask_ar[coupled_indices - 1] = 1
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
