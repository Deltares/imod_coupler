from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr


class ModMaxLayer:
    dataset: dict[str, Any]
    _file_name: str = "nodes_max_layer.tsv"

    def __init__(self, mod_id: xr.DataArray, mf6_max_layer: xr.DataArray) -> None:
        self.dataset = {}
        self._get_max_layer(mod_id, mf6_max_layer)

    def _get_max_layer(self, mod_id: xr.DataArray, mf6_max_layer: xr.DataArray) -> None:
        id = mod_id.isel(subunit=0)
        modid = id.where(id > 0).to_numpy().ravel()
        max_layer = mf6_max_layer.where(id > 0).to_numpy().ravel()
        self.dataset["mod_id"] = modid[np.isfinite(modid)].astype(dtype=np.int64)
        self.dataset["max_layer"] = max_layer[np.isfinite(max_layer)].astype(
            dtype=np.int64
        )

    def write(self, directory: str | Path) -> str:
        """
        Write mapping to .dxc file.

        Parameters
        ----------
        directory: str or Path
            directory in which exchange file should be written
        index: np.array

        """
        # Force to Path
        directory = Path(directory)
        # TODO: figure out how to please mypy with the slots here?

        pd.DataFrame(self.dataset).to_csv(
            directory / self._file_name, sep="\t", index=False
        )
        return f"./{directory.name}/{self._file_name}"
