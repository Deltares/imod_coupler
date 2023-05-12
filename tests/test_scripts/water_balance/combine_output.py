#!/usr/bin/env python

import re
from pathlib import Path

import netCDF4 as nc
import numpy as np

# import xlwt, xlrd
import pandas as pd
from test_scripts.water_balance.MF6_wbal_listing import listfile_to_dataframe
from test_scripts.water_balance.readfmhis import hisfile_to_dataframe
from test_scripts.water_balance.readmsw import totfile_to_dataframe


def writeNC(ncname: Path, df: pd.DataFrame, singlevar: bool):
    nvar = len(df.columns)
    ds = nc.Dataset(ncname, "w")
    ds.createDimension("time", len(df.index))
    #   create a separate variable "time" holding the record index
    #   timevar = ds.createVariable("time","f8",("time",))
    #   timevar[:] = np.array(df.index)
    if singlevar:
        namelen = 22
        ds.createDimension("id", len(df.columns))
        ds.createDimension("nchar", namelen)
        xchgvar = ds.createVariable(
            "exchange",
            "f8",
            (
                "time",
                "id",
            ),
        )
        namevar = ds.createVariable(
            "varname",
            "S1",
            (
                "id",
                "nchar",
            ),
        )
        xchgvar[:] = df.values

    for ivar in range(nvar):
        varname = df.columns[ivar]
        if singlevar:
            namevar[ivar] = nc.stringtochar(np.array([varname], "S%d" % namelen))
        else:
            xchgvar = ds.createVariable(varname, "f8", ("time",))
            xchgvar[:] = df[varname].values
    ds.close()


def writeXLS(xlsname: Path, df: pd.DataFrame) -> None:
    writer = pd.ExcelWriter(xlsname)
    df.to_excel(writer, sheet_name="combined")
    writer.save()


def writeCSV(csvname: Path, df: pd.DataFrame) -> None:
    colsep = ";"

    df.to_csv(csvname, sep=colsep, na_rep="nan")


def combine_dataframe(
      msw_totfile: Path, mf_listfile: Path
) -> pd.DataFrame:
    
    combined = pd.DataFrame()
   
   
    # MODFLOW in and out
    mf_listdf = listfile_to_dataframe(mf_listfile)
    mf6_daynrs = mf_listdf.iloc[:,1].values.astype(int)[:-1]
    msw_totdf = totfile_to_dataframe(msw_totfile).iloc[mf6_daynrs]

    # MetaSWAP incoming
    msw_sum_in = np.zeros(len(mf6_daynrs))
    for key in [
        "decSic",
        "decSpdmac",
        "decSpdmic",
        "Pm",
        "Psgw",
        "Pssw",
        "qrun",
        "qdr",
        "qmodf",
    ]:
        tmp = msw_totdf[key].values
        tmp[tmp < 0.0] = 0.0
        combined["msw_" + key + "_in"] = tmp
        msw_sum_in = msw_sum_in + msw_totdf[key].values
    combined["msw_decS_in"] = msw_totdf["decS_in"].values
    msw_sum_in = msw_sum_in + msw_totdf["decS_in"].values
    combined["msw_sum_in"] = msw_sum_in

    # MetaSWAP outgoing
    msw_sum_out = np.zeros(len(msw_totdf))
    for key in [
        "decSic",
        "decSpdmac",
        "decSpdmic",
        "Esp",
        "Eic",
        "Epd",
        "Ebs",
        "Tact",
        "qrun",
        "qdr",
        "qspgw",
        "qmodf",
    ]:
        tmp = msw_totdf[key].values
        tmp[tmp > 0.0] = 0.0
        combined["msw_" + key + "_out"] = tmp
        msw_sum_out = msw_sum_out + msw_totdf[key].values
    combined["msw_decS_out"] = msw_totdf["decS_out"].values
    msw_sum_out = msw_sum_out + msw_totdf["decS_out"].values
    combined["msw_sum_out"] = msw_sum_out
    print("Reading MetaSWAP data finished")


    direction = ["IN", "OUT"]
    modflow_fields = ["STO", "STO-SS", "CHD", "DRN", "RIV", "WEL", "DXC", "RCH"]

    combined.insert(0,"timestep",  mf_listdf["timestep"])
    combined.insert(1,"stress_period" ,mf_listdf["stress_period"])
    # init all sums to NaN
    for key1 in direction:
        for key2 in modflow_fields:
            combinedname = "mf_%s_%s" % (key2, key1)
            combined[combinedname] = np.NaN  # 0.0

    # total by package type and direction
    for lbl in list(mf_listdf):
        m = re.match(r"(.*):.*_((IN|OUT)$)", lbl)
        if m:
            combinedname = "mf_%s_%s" % (m.group(1), m.group(2))
            if all(np.isnan(combined[combinedname])):
                combined[combinedname] = 0.0
            combined[combinedname] += mf_listdf[lbl]

    print("Reading ModFLOW data finished")

    return combined