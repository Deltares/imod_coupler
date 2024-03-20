import abc
from io import TextIOWrapper
from pathlib import Path
from typing import Any

import pandas as pd
import xarray as xr
from imod.msw.fixed_format import VariableMetaData, format_fixed_width
from numpy.typing import NDArray


class GenericMapping(abc.ABC):
    name: str
    dataframe: pd.DataFrame

    def write(self, directory: Path) -> str:
        """
        Write mapping to .tsv  file

        Parameters
        ----------
        directory: str or Path
            directory in which exchange file should be written

        """
        filename = f"{self.name}.tsv"
        self.dataframe.to_csv(directory / filename, sep="\t", index=False)
        return f"./{directory.name}/{filename}"


class MetaModMapping(abc.ABC):
    """
    MappingBase is used to share methods for specific packages with no time
    component for multiple two-component mappings.

    It is intended as an abstract base class, only to inherit from, to implement new
    packages.
    """

    __slots__ = "_pkg_id", "dataset", "index"
    _metadata_dict: dict[str, VariableMetaData]
    _with_subunit: tuple[str, str, str]
    _to_fill: tuple[str]
    _file_name: str

    def __init__(self) -> None:
        self.dataset = xr.Dataset()

    def __getitem__(self, key: str) -> Any:
        return self.dataset.__getitem__(key)

    def __setitem__(self, key: str, value: Any) -> None:
        self.dataset.__setitem__(key, value)

    def isel(self) -> None:
        raise NotImplementedError(
            "Selection on packages not yet supported. "
            "To make a selection on the xr.Dataset, call dataset.isel instead. "
            "You can create a new package with a selection by calling (**dataset.isel(**selection))"
        )

    def sel(self) -> None:
        raise NotImplementedError(
            "Selection on packages not yet supported. "
            "To make a selection on the xr.Dataset, call dataset.sel instead. "
            "You can create a new package with a selection by calling (**dataset.sel(**selection))"
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

    def write_dataframe_fixed_width(
        self, file: TextIOWrapper, dataframe: pd.DataFrame
    ) -> None:
        for row in dataframe.itertuples():
            for index, metadata in enumerate(self._metadata_dict.values()):
                content = format_fixed_width(row[index + 1], metadata)
                file.write(content)
            file.write("\n")

    def _index_da(self, da: pd.DataFrame, index: NDArray[Any]) -> Any:
        return da.to_numpy().ravel()[index]

    def _render(
        self, file: TextIOWrapper, index: NDArray[Any], svat: pd.DataFrame
    ) -> None:
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
        index = self.index  # type: ignore

        with open(directory / self._file_name, "w") as f:
            self._render(f, index=index, svat=self.dataset["svat"])
        return f"./{directory.name}/{self._file_name}"
