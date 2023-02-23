#!/usr/bin/env python
# type: ignore
import os
import sys

from combine_output import combineDF, writeCSV, writeNC, writeXLS

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
