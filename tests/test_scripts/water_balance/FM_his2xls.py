#!/usr/bin/env python
# type: ignore
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

fields = {
    "time": "",
    "water_balance_storage": "storage",
    "water_balance_total_volume": "total volume",
    "water_balance_boundaries_in": "boundaries in",
    "water_balance_precipitation_total": "precip total",
    "water_balance_Qext_in_1D": "Qext_in_1D",
    "water_balance_Qext_in_2D": "Qext_in_2D",
    "water_balance_boundaries_out": "boundaries out",
    "water_balance_evaporation": "evaporation",
    "water_balance_Qext_out_1D": "Qext_out_1D",
    "water_balance_Qext_out_2D": "Qext_out_2D",
    "water_balance_laterals_in_1D": "laterals_in_1D",
    "water_balance_laterals_out_1D": "laterals_in_1D",
}

for key, value in fields.items():
    if value == "":
        fields[key] = key

hisname = sys.argv[1]
csvname = osp.splitext(hisname)[0] + ".csv"
xlsname = osp.splitext(hisname)[0] + ".xlsx"

ds = nc.Dataset(hisname, "r")
datadict = {}
alltimes = ds.variables["time"][:]

sel = alltimes % 86400 == 0
nsel = np.count_nonzero(sel)
for fieldname in fields:
    datadict[fieldname] = ds.variables[fieldname][sel]

with open(csvname, "w") as fcsv:
    valuelist = [hdrfmt % var for key, var in fields.items()]
    fcsv.write("%s\n" % colsep.join(valuelist))
    for ndx in range(nsel):
        valuelist = [colfmt % var[ndx] for key, var in datadict.items()]
        fcsv.write("%s\n" % colsep.join(valuelist))

# using time as index
# hisdf = pd.DataFrame(index=datadict['time'])
# for key, var in datadict.items():
#    if key!='time':
#        hisdf[fields[key]] = var


# without explicit index
hisdf = pd.DataFrame()
for key, var in datadict.items():
    hisdf[fields[key]] = var

# write directly to xls-file
# hisdf.to_excel(xlsname, sheet_name=fm_sheet_name)

# write to xls-file using an excel-writer instance
writer = pd.ExcelWriter(xlsname)
hisdf.to_excel(writer, sheet_name=fm_sheet_name)
for column in hisdf:
    column_length = max(hisdf[column].astype(str).map(len).max(), len(column))
    col_idx = hisdf.columns.get_loc(column)
    writer.sheets[fm_sheet_name].set_column(col_idx, col_idx, column_length)
writer.save()


sys.stderr.write("Done!")
