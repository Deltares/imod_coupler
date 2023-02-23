#!/usr/bin/env python
import os
import pprint as pp
import re
import sys

import MF6_wbal_listing as readmf6
import netCDF4 as nc
import numpy as np

# import xlwt, xlrd
import openpyxl
import pandas as pd
import readfmhis as readdfm
import readmsw as readmsw
from xlutils.copy import copy as xl_copy


def writeWorksheet(workbook, sheetname, df):
    newsheet = workbook.add_sheet(sheetname)
    nrows = len(df)
    ncols = len(df.columns)
    for j in range(ncols):
        newsheet.write(0, j, j)
        newsheet.write(1, j, df.columns[j])
    for i in range(nrows):
        record = list(df.iloc[i])
        for j in range(ncols):
            newsheet.write(i + 2, j, float(record[j]))


def writeNC(ncname, df, singlevar):
    nvar = len(df.columns)
    ds = nc.Dataset(ncname, "w")
    timeDim = ds.createDimension("time", len(df.index))
    #   create a separate variable "time" holding the record index
    #   timevar = ds.createVariable("time","f8",("time",))
    #   timevar[:] = np.array(df.index)
    if singlevar:
        namelen = 22
        idDim = ds.createDimension("id", len(df.columns))
        chDim = ds.createDimension("nchar", namelen)
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


def writeXLS(xlsname, df):
    writer = pd.ExcelWriter(xlsname)
    df.to_excel(writer, sheet_name="combined")
    writer.save()


def writeCSV(csvname, df):
    colsep = ";"
    colfmt = "%15.3f"
    hdrfmt = "%15s"

    with open(csvname, "w") as fcsv:
        valuelist = list(df)
        fcsv.write("%s\n" % colsep.join(valuelist))
        for ndx in range(len(df)):
            record = list(df.iloc[ndx])
            valuelist = [colfmt % float(var) for var in record]
            fcsv.write("%s\n" % colsep.join(valuelist))


def combineDF(**kwargs):
    fm_interval = 1  # set to 1 to retrieve all time levels
    fm_interval = 86400

    fm_hisfile = kwargs["fm"]
    msw_totfile = kwargs["msw"]
    mf_listfile = kwargs["mf"]

    fm_hisdf, fm_hisdf_rates = readdfm.hisfile2df(fm_hisfile, fm_interval)

    combined = fm_hisdf_rates.copy()

    renaming = {key: "fm_" + key for key in list(combined) if key not in ["t"]}
    combined.rename(columns=renaming, inplace=True)
    print("Reading DFlowFM data finished")

    # mf6_daynrs = [int(fm_hisdf.at[i,'time'] / 86400) for i in range(len(fm_hisdf))]
    # 86400 sec in dfm is at the end of the first modflow day, that is record 0 !!
    mf6_daynrs = [int(time_seconds / 86400.0 - 0.5) for time_seconds in fm_hisdf["t"]]
    msw_totdf = readmsw.totfile2df(msw_totfile).iloc[mf6_daynrs]

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

    # MODFLOW in and out
    mf_listdf, mf_listdf_cum = readmf6.listfile2df(mf_listfile)

    direction = ["IN", "OUT"]
    modflow_fields = ["STO", "STO-SS", "CHD", "DRN", "RIV", "WEL", "DXC", "RCH"]

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

    combined["t"] = (
        combined["t"] / 86400.0
    )  # time was the fm time in seconds, now converted into days
    return combined


if __name__ == "__main__":
    fm_hisfile = sys.argv[1]
    msw_totfile = sys.argv[2]
    mf_listfile = sys.argv[3]
    outname = sys.argv[4]  # requires 4 arguments, three reffering to input files
    # and one to the output name without extension
    combined = combineDF(fm=sys.argv[1], msw=sys.argv[2], mf=sys.argv[3])
    nc_out = outname + ".nc"
    xls_out = outname + ".xlsx"
    csv_out = outname + ".csv"

    print("Writing NetCDF")
    writeNC(nc_out, combined, singlevar=False)
    print("Writing CSV")
    writeCSV(csv_out, combined)
    print("Writing XLSX")
    writeXLS(xls_out, combined)
    sys.stderr.write("done!")
else:
    sys.stderr.write(
        "imported, use function CombineDF(fm_hisfile, msw_totfile, mf_listfile) to obtain the combined dataframe."
    )