from pathlib import Path

import netCDF4 as nc
import numpy as np

# import xlwt, xlrd
import pandas as pd
from test_scripts.mf6_water_balance.MF6_wbal_listing import listfile_to_dataframe


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


def combine_dataframe(msw_totfile: Path, mf_listfile: Path) -> pd.DataFrame:
    # MODFLOW in and out
    mf_listdf = listfile_to_dataframe(mf_listfile)
    print("Reading ModFLOW data finished")

    return mf_listdf
