#!/usr/bin/env python

from pathlib import Path
from typing import Union

from test_scripts.water_balance.MF6_wbal_listing import listfile_to_dataframe
from test_scripts.water_balance.combine_output import writeCSV, writeNC, writeXLS

def create_modflow_waterbalance_file(
    mf_listfile: Path,
    output_file_xlsx: Union[Path, None] = None,
    output_file_netcdf: Union[Path, None] = None,
    output_file_csv: Union[Path, None] = None
) -> None:
    modflow_results_dataframe =  listfile_to_dataframe(mf_listfile)

    if output_file_netcdf is not None:
        print("Writing NetCDF")
        writeNC(output_file_netcdf, modflow_results_dataframe, singlevar=False)
    if output_file_csv is not None:
        print("Writing CSV")
        writeCSV(output_file_csv, modflow_results_dataframe)
    if output_file_xlsx is not None:
        print("Writing XLSX")
        writeXLS(output_file_xlsx, modflow_results_dataframe)
