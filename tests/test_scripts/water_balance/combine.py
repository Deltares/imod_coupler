#!/usr/bin/env python

from pathlib import Path
from typing import Union

from .combine_output import *


def create_waterbalance_file(
    fm_hisfile: Path,
    msw_totfile: Path,
    mf_listfile: Path,
    output_file_xlsx: Union[Path, None] = None,
    output_file_netcdf: Union[Path, None] = None,
    output_file_csv: Union[Path, None] = None,
) -> None:
    combined_dataframe = combine_dataframe(
        fm_hisfile, msw_totfile, mf_listfile
    )

    if output_file_netcdf is not None:
        print("Writing NetCDF")
        writeNC(output_file_netcdf, combined_dataframe, singlevar=False)
    if output_file_csv is not None:
        print("Writing CSV")
        writeCSV(output_file_csv, combined_dataframe)
    if output_file_xlsx is not None:
        print("Writing XLSX")
        writeXLS(output_file_xlsx, combined_dataframe)
