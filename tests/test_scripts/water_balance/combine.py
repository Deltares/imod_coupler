#!/usr/bin/env python

from pathlib import Path

from test_scripts.water_balance.combine_output import (
    combineDF,
    writeCSV,
    writeNC,
    writeXLS,
)


def create_waterbalance_file(
    fm_hisfile: Path,
    msw_totfile: Path,
    mf_listfile: Path,
    output_file_xlsx: Path = None,
    output_file_netcdf: Path = None,
    output_file_csv: Path = None,
) -> None:
    combined_dataframe = combineDF(fm_hisfile, msw_totfile, mf_listfile)

    if output_file_netcdf is not None:
        print("Writing NetCDF")
        writeNC(output_file_netcdf, combined_dataframe, singlevar=False)
    if output_file_csv is not None:
        print("Writing CSV")
        writeCSV(output_file_csv, combined_dataframe)
    if output_file_xlsx is not None:
        print("Writing XLSX")
        writeXLS(output_file_xlsx, combined_dataframe)
