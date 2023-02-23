#!/usr/bin/env python
import os.path as osp
import pprint as pp
import sys

import netCDF4 as nc
import numpy as np
import pandas as pd
from openpyxl import load_workbook

colsep = ";"
colfmt = "%15.3f"
hdrfmt = "%15s"
fm_sheet_name = "FM-his"


def hisfile2df(hisname, interval):
    fields = {
        "time": "t",
        "water_balance_boundaries_in": "bndin",
        "water_balance_precipitation_total": "prec",
        "water_balance_Qext_in_1D": "qin1d",
        "water_balance_Qext_in_2D": "qin2d",
        "water_balance_laterals_in_1D": "latin1d",
        "water_balance_boundaries_out": "bndout",
        "water_balance_evaporation": "evap",
        "water_balance_Qext_out_1D": "qout1d",
        "water_balance_Qext_out_2D": "qout2d",
        "water_balance_laterals_out_1D": "latout1d",
    }

    for key, value in fields.items():
        if value == "":
            fields[key] = key

    ds = nc.Dataset(hisname, "r")
    alltimes = ds.variables["time"][:]

    sel = alltimes % interval == 0
    nsel = np.count_nonzero(sel)
    hisdf = pd.DataFrame()
    for ncname, dfname in fields.items():
        hisdf[dfname] = ds.variables[ncname][sel]

    # Add accumulated storage, positive and negative
    stor = np.insert(ds.variables["water_balance_storage"][sel], 0, 0)
    dstorpos = stor[1:] - stor[:-1]
    dstorneg = stor[1:] - stor[:-1]
    dstorpos[dstorpos < 0.0] = 0.0
    dstorneg[dstorneg > 0.0] = 0.0
    storpos = np.cumsum(dstorpos)
    storneg = -np.cumsum(dstorneg)
    hisdf["stoin"] = storpos
    hisdf["stoout"] = storneg

    totals_out = storneg[:]

    for key in ["bndout", "evap", "qout1d", "qout2d", "latout1d"]:
        hisdf[key] = -hisdf[key]
        totals_out = totals_out + np.array(hisdf[key][:])
    totals_in = storpos[:]
    for key in ["bndin", "prec", "qin1d", "qin2d", "latin1d"]:
        totals_in = totals_in + np.array(hisdf[key][:])
    hisdf["totalin"] = totals_in
    hisdf["totalout"] = totals_out
    hisdf["totalin+out"] = totals_in + totals_out

    ds.close()

    hisdf_rates = pd.DataFrame()
    # create derived dataframes with increments day to day, except for time
    hisdf_rates["t"] = hisdf["t"]
    fields = list(hisdf)
    fields.remove("t")
    for key in fields:
        tmp = np.insert(np.array(hisdf[key]), 0, 0)
        hisdf_rates[key] = tmp[1:] - tmp[:-1]
    return hisdf, hisdf_rates


def writeCSV(csvname, hisdf):
    with open(csvname, "w") as fcsv:
        valuelist = list(hisdf)
        fcsv.write("%s\n" % colsep.join(valuelist))
        for ndx in range(len(hisdf)):
            record = list(hisdf.iloc[ndx])
            valuelist = [colfmt % var for var in record]
            fcsv.write("%s\n" % colsep.join(valuelist))


def writeXLS(xlsname, hisdf):
    writer = pd.ExcelWriter(xlsname)
    hisdf.to_excel(writer, sheet_name=fm_sheet_name)
    for column in hisdf:
        column_length = max(hisdf[column].astype(str).map(len).max(), len(column))
        col_idx = hisdf.columns.get_loc(column)
    #       writer.sheets[fm_sheet_name].set_column(col_idx, col_idx, column_length)
    writer.save()


if __name__ == "__main__":
    name = sys.argv[1]
    outname = sys.argv[2]
    hisdf, hisdf_rates = hisfile2df(hisname, 86400)
    writeCSV(outname + ".csv", hisdf)
    writeXLS(outname + ".xls", hisdf)
    writeCSV(outname + "_rates.csv", hisdf_rates)
    writeXLS(outname + "_rates.xls", hisdf_rates)
    sys.stderr.write("Done!")
