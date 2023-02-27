#!/usr/bin/env python

import re

import numpy as np
import pandas as pd
from dateutil import parser as dp

# selection of output variables from the MetaSWAP csv
varsel = [
    "Pssw",  # sprinkling precipitation, from surface water
    "qrun",  # runon
    "qdr",  # net infltration of surface water
    "Psswdem",  # sprinkling from surface water demand
    "mod2dfmdef",  # temporary deficit in exchange scheme with DFM
    "qinf",  # infiltration on soil surface (total)
]


def totfile2df(msw_totfile):
    df = pd.read_csv(msw_totfile, parse_dates=True)
    oldhdr = list(df)
    newhdr = [re.sub(r"\s+", "_", re.sub(r"\(.+\)", "", hdr).strip()) for hdr in oldhdr]
    rename = {old: new for old, new in zip(oldhdr[:-1], newhdr[1:])}
    msw_totdf = df.rename(columns=rename)

    # convert index which are date strings to seconds since begin simulation
    first = dp.isoparse(msw_totdf.index[1])
    offset = first - dp.isoparse(msw_totdf.index[0])
    seconds = []
    for datestr in list(msw_totdf.index):
        realdate = dp.isoparse(datestr)
        timedelta = 2 * offset + realdate - first  # first line is after first timestep
        timedelta = offset + realdate - first  # first line is before first timestep
        seconds.append(timedelta.seconds + 86400 * timedelta.days)
    msw_totdf["seconds"] = seconds

    # sum storage in all layers decS00 ... decSXX, sum negative and positive values separately
    msw_totdf["decS_in"] = 0
    msw_totdf["decS_out"] = 0
    for colname in list(msw_totdf):
        if re.match(r"decS\d{2}", colname):
            msw_totdf["decS_in"] = msw_totdf["decS_in"] + [
                max(colvalue, 0.0) for colvalue in np.array(msw_totdf[colname])
            ]
            msw_totdf["decS_out"] = msw_totdf["decS_out"] + [
                min(colvalue, 0.0) for colvalue in np.array(msw_totdf[colname])
            ]

    return msw_totdf
