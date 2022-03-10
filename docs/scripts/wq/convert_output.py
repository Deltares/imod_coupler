import imod
import numpy as np
import xarray as xr

# We assume that this script is located in the same directory
# as in create_wq_input.py.
# We provide a UNIX style global path
# to select all IDF files in the conc directory.
conc_path = "./results/conc/*.IDF"
bottom_path = "./FreshwaterLens/bas/bottom*.idf"
top_path = "./FreshwaterLens/bas/top.idf"

# Open the IDF files.
conc = imod.idf.open(conc_path).compute()
bottom = imod.idf.open(bottom_path).compute()
surface = imod.idf.open(top_path).compute()

# Reconstruct vertical discretization
# We need this as IDFs do not store vertical discretization
surface = surface.assign_coords(layer=1)

## Create 3D array of tops
### Roll bottom one layer downward: the bottom of a layer is top of next layer
top = bottom.roll(layer=1, roll_coords=False)
### Remove layer 1
top = top.sel(layer=slice(2, None))
### Add surface as layer 1
top = xr.concat([surface, top], dim="layer")
### Reorder dimensions
top = top.transpose("layer", "y", "x")

# Merge into dataset
ds = xr.merge([conc, top, bottom])

# Create MDAL supported UGRID
# NOTE: This requires iMOD-python v1.0(?)
ds_ugrid = imod.util.to_ugrid2d(ds)

#%% Due to a bug in MDAL, we have to encode the times as floats
# instead of integers
# until this is fixed: https://github.com/lutraconsulting/MDAL/issues/348
ds_ugrid["time"].encoding["dtype"] = np.float64

ds_ugrid.to_netcdf("./results/output_ugrid.nc")
