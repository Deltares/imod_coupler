#!/usr/bin/env python

from pathlib import Path

import h5netcdf.legacyapi as nc
import numpy as np
import pandas as pd

from test_scripts.mf6_water_balance.MF6_wbal_listing import listfile_to_dataframe


def create_modflow_waterbalance_file(
    mf_listfile: Path,
    output_file_xlsx: Path | None = None,
    output_file_netcdf: Path | None = None,
    output_file_csv: Path | None = None,
) -> None:
    """
    this function creates a csv, excel or netcdf file with the water-balance information found in
    the .lst file of the modflow groundwater flow model
    """
    modflow_results_dataframe = listfile_to_dataframe(mf_listfile)

    if output_file_netcdf is not None:
        print("Writing NetCDF")
        writeNC(output_file_netcdf, modflow_results_dataframe, singlevar=False)
    if output_file_csv is not None:
        print("Writing CSV")
        writeCSV(output_file_csv, modflow_results_dataframe)
    if output_file_xlsx is not None:
        print("Writing XLSX")
        writeXLS(output_file_xlsx, modflow_results_dataframe)


def writeNC(ncname: Path, df: pd.DataFrame, singlevar: bool):
    nvar = len(df.columns)
    with nc.Dataset(ncname, "w") as ds:
        ds.createDimension("time", len(df.index))
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
            xchgvar[:] = df.to_numpy()

        for ivar in range(nvar):
            varname = df.columns[ivar]
            if singlevar:
                namevar[ivar] = nc.stringtochar(np.array([varname], "S%d" % namelen))
            else:
                xchgvar = ds.createVariable(varname, "f8", ("time",))
                xchgvar[:] = df[varname].to_numpy()


def writeXLS(xlsname: Path, df: pd.DataFrame) -> None:
    writer = pd.ExcelWriter(xlsname)
    df.to_excel(writer, sheet_name="combined")
    writer.save()


def writeCSV(csvname: Path, df: pd.DataFrame) -> None:
    colsep = ";"

    df.to_csv(csvname, sep=colsep, na_rep="nan")
