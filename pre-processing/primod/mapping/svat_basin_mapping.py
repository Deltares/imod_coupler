from pathlib import Path

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
        self.dataset = pd.DataFrame(
            data={"basin_index": basin_index, "bound_index": boundary_index_values}
        )

    def write(self, directory: str | Path) -> str:
        """
        Write mapping to .tsv  file

        Parameters
        ----------
        directory: str or Path
            directory in which exchange file should be written

        """
        filename = f"{self.name}.tsv"
        self.dataset.to_csv(directory / filename, sep="\t", index=False)
        return filename
