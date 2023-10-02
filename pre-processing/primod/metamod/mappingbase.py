import abc
from pathlib import Path
from typing import Any, Union

import numpy as np
import pandas as pd
import xarray as xr
from imod.msw.fixed_format import VariableMetaData, format_fixed_width


class MetaModMapping(abc.ABC):
    """
    MetaModMapping is used to share methods for specific packages with no time
    component.

    It is not meant to be used directly, only to inherit from, to implement new
    packages.
    """

    __slots__ = "_pkg_id"
    _metadata_dict: dict[str, VariableMetaData]

    def __init__(self) -> None:
        self.dataset = xr.Dataset()

    def __getitem__(self, key: str) -> Any:
        return self.dataset.__getitem__(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.dataset.__setitem__(key, value)

    def isel(self) -> None:
        raise NotImplementedError(
            f"Selection on packages not yet supported. "
            f"To make a selection on the xr.Dataset, call {self._pkg_id}.dataset.isel instead. "
            f"You can create a new package with a selection by calling {__class__.__name__}(**{self._pkg_id}.dataset.isel(**selection))"
        )

    def sel(self) -> None:
        raise NotImplementedError(
            f"Selection on packages not yet supported. "
            f"To make a selection on the xr.Dataset, call {self._pkg_id}.dataset.sel instead. "
            f"You can create a new package with a selection by calling {__class__.__name__}(**{self._pkg_id}.dataset.sel(**selection))"
        )

    def _check_range(self, dataframe: pd.DataFrame) -> None:
        for varname in dataframe:
            min_value = self._metadata_dict[varname].min_value
            max_value = self._metadata_dict[varname].max_value
            if (dataframe[varname] < min_value).any() or (
                dataframe[varname] > max_value
            ).any():
                raise ValueError(
                    f"{varname}: not all values are within range ({min_value}-{max_value})."
                )

    def write_dataframe_fixed_width(self, file, dataframe: pd.DataFrame) -> None:
        for row in dataframe.itertuples():
            for index, metadata in enumerate(self._metadata_dict.values()):
                content = format_fixed_width(row[index + 1], metadata)
                file.write(content)
            file.write("\n")

    def _index_da(self, da, index) -> Any:
        return da.to_numpy().ravel()[index]

    def _render(self, file, index, svat) -> None:
        data_dict = {"svat": svat.to_numpy().ravel()[index]}

        for var in self._with_subunit:
            data_dict[var] = self._index_da(self.dataset[var], index)

        for var in self._to_fill:
            data_dict[var] = ""

        dataframe = pd.DataFrame(
            data=data_dict, columns=list(self._metadata_dict.keys())
        )

        self._check_range(dataframe)
        self.write_dataframe_fixed_width(file, dataframe)

    def write(self, directory: Union[str, Path], index: np.array, svat: xr.DataArray) -> None:
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

        filename = directory / self._file_name
        with open(filename, "w") as f:
            self._render(f, index, svat)
