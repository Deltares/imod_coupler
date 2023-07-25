# %%
import os
from pathlib import Path

import dask.array as da
import imod
import numpy as np
import pandas as pd


def split_heads_file(
    sdate: str,
    hds_file: Path,
    grb_file: Path,
    n_repeat: int,
    file_out: Path,
    idf: bool,
    ncdf: bool,
) -> None:
    heads = imod.mf6.open_hds(hds_file, grb_file)
    total_periods = heads.shape[0]
    original_periods = total_periods / n_repeat
    nsubsets = int(total_periods / original_periods)
    istart = 1
    for isubset in np.arange(nsubsets):
        subset = heads.sel(time=slice(istart, istart + original_periods - 1))
        subset = subset.assign_coords(coords={"time": np.arange(original_periods) + 1})
        starttime = pd.to_datetime(sdate)
        timedelta = pd.to_timedelta(subset["time"], "D")
        subset = subset.assign_coords(time=starttime + timedelta)
        os.makedirs(str(file_out).format(imodel=isubset))
        if ncdf:
            subset.to_netcdf(str(file_out).format(imodel=isubset) + "/heads.nc")
        if idf:
            imod.idf.save(str(file_out).format(imodel=isubset) + "/heads.idf", subset)
        istart += original_periods
