import numpy as np
import pandas as pd
import xarray as xr
from numpy.typing import NDArray

from primod.mapping.mappingbase import GenericMapping
from primod.typing import Int


class SvatUserDemandMapping(GenericMapping):
    def __init__(
        self,
        name: str,
        gridded_user_demand: xr.DataArray,
        user_demand_ids: pd.Series,
        svat: xr.DataArray,
        index: NDArray[Int],
    ):
        condition = svat > 0
        user_id = xr.where(condition, gridded_user_demand, np.nan)  # type: ignore
        include = user_id.notnull().to_numpy()
        user_id_values = user_id.to_numpy()[include].astype(int)
        user_index = np.searchsorted(user_demand_ids, user_id_values)

        coupled_svats = svat.where(gridded_user_demand.notnull(), other=-1)
        # Set all "deeper" subunits (higher than 0) to -1 so they are filtered away.
        coupled_svats.loc[{"subunit": slice(1, None)}] = -1
        svat_index_values = coupled_svats.to_numpy().ravel()[index]
        svat_index_values = svat_index_values[svat_index_values > 0].astype(int)

        self.name = name
        self.dataframe = pd.DataFrame(
            data={"user_demand_index": user_index, "svat_index": svat_index_values}
        )
