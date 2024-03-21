import numpy as np
import pandas as pd
import xarray as xr
from numpy.typing import NDArray

from primod.mapping.mappingbase import GenericMapping
from primod.typing import Int


class SvatBasinMapping(GenericMapping):
    def __init__(
        self,
        name: str,
        gridded_basin: xr.DataArray,
        basin_ids: pd.Series,
        svat: xr.DataArray,
        index: NDArray[Int],
    ):
        condition = svat > 0
        basin_id = xr.where(condition, gridded_basin, np.nan)  # type: ignore
        include = basin_id.notnull().to_numpy()
        basin_id_values = basin_id.to_numpy()[include].astype(int)
        basin_index = np.searchsorted(basin_ids, basin_id_values)

        # TODO (Huite): I'm not entirely sure this is the correct logic!
        # I don't quite understand the whole index business.
        # This should probably be simplified for all MetaModMappings too.
        coupled_svats = svat.isel(subunit=0, drop=True).where(
            gridded_basin.notnull(), other=-1
        )
        svat_index_values = coupled_svats.to_numpy().ravel()[index]
        svat_index_values = svat_index_values[svat_index_values > 0].astype(int)

        self.name = name
        self.dataframe = pd.DataFrame(
            data={"basin_index": basin_index, "svat_index": svat_index_values}
        )
