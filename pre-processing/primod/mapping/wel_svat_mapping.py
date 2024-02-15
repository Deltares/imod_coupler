from io import TextIOWrapper
from typing import Any

import numpy as np
import pandas as pd
import xarray as xr
from imod import mf6
from imod.msw.fixed_format import VariableMetaData
from numpy.typing import NDArray
from primod.mapping.mappingbase import MetaModMapping


class WellSvatMapping(MetaModMapping):
    """
    This contains the data to connect MODFLOW 6 well cells to MetaSWAP svats.

    This class is responsible for the file `wellindex2svat.dxc`.

    Parameters
    ----------
    svat: array of floats (xr.DataArray)
        SVAT units. This array must have a subunit coordinate to describe
        different land uses.
    well: mf6.Well
        Modflow 6 Well package to connect to.
    """

    _file_name = "wellindex2svat.dxc"
    _metadata_dict = {
        "wel_id": VariableMetaData(10, 1, 9999999, int),
        "free": VariableMetaData(2, None, None, str),
        "svat": VariableMetaData(10, 1, 9999999, int),
        "layer": VariableMetaData(5, 0, 9999, int),
    }

    _with_subunit = ("wel_id", "svat", "layer")
    _to_fill = ("free",)

    def __init__(self, svat: xr.DataArray, well: mf6.WellDisStructured):
        super().__init__()
        self.well = well
        well_mod_id, well_svat, layer = self._create_well_id(svat)
        self.dataset["wel_id"] = well_mod_id
        self.dataset["svat"] = well_svat
        self.dataset["layer"] = layer

    def _create_well_id(
        self, svat: pd.DataFrame
    ) -> tuple[NDArray[Any], NDArray[Any], NDArray[Any]]:
        """
        Get modflow indices, svats, and layer number for the wells
        """
        # Convert to Python's 0-based index
        well_row = self.well["row"] - 1
        well_column = self.well["column"] - 1
        well_layer = self.well["layer"]

        n_subunit = svat["subunit"].size

        well_svat = svat.to_numpy()[:, well_row, well_column]
        well_active = well_svat != 0

        well_svat_1d = well_svat[well_active]

        # Tile well_layers for each subunit
        layer = np.tile(well_layer, (n_subunit, 1))
        layer_1d = layer[well_active]

        well_id = self.well.dataset.coords["index"] + 1
        well_id_1d = np.tile(well_id, (n_subunit, 1))[well_active]

        return (well_id_1d, well_svat_1d, layer_1d)

    def _render(self, file: TextIOWrapper, *args: Any) -> None:
        data_dict: dict[str, Any] = {}
        data_dict["svat"] = self.dataset["svat"].to_numpy()
        data_dict["layer"] = self.dataset["layer"].to_numpy()
        data_dict["wel_id"] = self.dataset["wel_id"].to_numpy()

        for var in self._to_fill:
            data_dict[var] = ""

        dataframe = pd.DataFrame(
            data=data_dict, columns=list(self._metadata_dict.keys())
        )

        self._check_range(dataframe)
        self.write_dataframe_fixed_width(file, dataframe)
