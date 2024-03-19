import numpy as np
import pandas as pd
import xarray as xr

from primod.mapping.mappingbase import GenericMapping


class SvatBasinMapping(GenericMapping):
    def __init__(
        self,
        name: str,
        gridded_basin: xr.DataArray,
        basin_ids: pd.Series,
        condition: xr.DataArray,
    ):
        basin_id = xr.where(condition, gridded_basin, np.nan)  # type: ignore
        include = basin_id.notnull().to_numpy()
        basin_id_values = basin_id.to_numpy()[include].astype(int)
        basin_index = np.searchsorted(basin_ids, basin_id_values)
        boundary_index_values = np.arange(np.size(basin_index))
        self.name = name
        self.dataframe = pd.DataFrame(
            data={"basin_index": basin_index, "bound_index": boundary_index_values}
        )
