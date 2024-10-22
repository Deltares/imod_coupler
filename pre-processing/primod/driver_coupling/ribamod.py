import abc
from pathlib import Path
from typing import Any

import imod
import numpy as np
import pandas as pd
import ribasim
import xarray as xr
from geopandas import gpd

from primod.driver_coupling.driver_coupling_base import DriverCoupling
from primod.driver_coupling.util import (
    _nullify_ribasim_exchange_input,
    _validate_node_ids,
)
from primod.mapping.node_basin_mapping import ActiveNodeBasinMapping, NodeBasinMapping


class RibaModDriverCoupling(DriverCoupling, abc.ABC):
    """A dataclass representing one coupling scenario for the RibaMod driver.

    Attributes
    ----------
    mf6_model: str
        The name of the GWF model
    ribasim_basin_definition : gpd.GeoDataFrame, xr.Dataset
        * GeoDataFrame: basin polygons
        * Dataset: mapping of mf6 package name to grid containing basin IDs.
    mf6_packages : list of str
        A list of river or drainage packages.
    subgrid_id_range: optional DataFrame containing min and max subgrid_id per mf6_package
    """

    mf6_model: str
    ribasim_basin_definition: (
        gpd.GeoDataFrame | xr.Dataset
    )  # TODO: hopefully pydantic is happy
    mf6_packages: list[str]
    subgrid_id_range: pd.DataFrame | None = None

    @abc.abstractmethod
    def derive_mapping(
        self,
        name: str,
        conductance: xr.DataArray,
        gridded_basin: xr.DataArray,
        basin_ids: pd.Series,
        ribasim_model: ribasim.Model,
    ) -> NodeBasinMapping | ActiveNodeBasinMapping:
        pass

    @abc.abstractproperty
    def _prefix(self) -> str:
        pass

    @staticmethod
    def _empty_coupling_dict() -> dict[str, Any]:
        return {
            "mf6_active_river_packages": {},
            "mf6_passive_river_packages": {},
            "mf6_active_drainage_packages": {},
            "mf6_passive_drainage_packages": {},
        }

    def write_exchanges(
        self,
        directory: Path,
        coupled_model: Any,
    ) -> dict[str, Any]:
        mf6_simulation = coupled_model.mf6_simulation
        gwf_model = mf6_simulation[self.mf6_model]
        ribasim_model = coupled_model.ribasim_model

        dis = gwf_model[gwf_model._get_pkgkey("dis")]
        basin_definition = self.ribasim_basin_definition
        if isinstance(basin_definition, gpd.GeoDataFrame):
            # Validate and fetch
            basin_ids = _validate_node_ids(
                ribasim_model.basin.node.df, basin_definition
            )
            gridded_basin = imod.prepare.rasterize(
                basin_definition,
                like=dis["idomain"].isel(layer=0, drop=True),
                column="node_id",
            )
            basin_dataset = xr.Dataset(
                {key: gridded_basin for key in self.mf6_packages}
            )
        elif isinstance(basin_definition, xr.Dataset):
            basin_ids = _validate_node_ids(
                ribasim_model.basin.node.df, basin_definition[self.mf6_packages]
            )
            basin_dataset = basin_definition
        else:
            raise TypeError(
                "Expected geopandas.GeoDataFrame or xr.Dataset: "
                f"received {type(basin_definition.__name__)}"
            )

        # drainage and infiltration to NoData later on.
        coupling_dict = self._empty_coupling_dict()
        coupling_dict["mf6_model"] = self.mf6_model
        coupled_basin_indices = []
        for gwf_package_key in self.mf6_packages:
            gridded_basin = basin_dataset[gwf_package_key]
            filename, destination, basin_index = self._write_exchange(
                directory,
                gwf_model,
                gwf_package_key,
                ribasim_model,
                basin_ids,
                gridded_basin,
            )
            coupling_dict[f"mf6_{self._prefix}_{destination}_packages"][
                gwf_package_key
            ] = filename
            coupled_basin_indices.append(basin_index)

        coupled_basin_indices = np.unique(np.concatenate(coupled_basin_indices))
        coupled_basin_node_ids = basin_ids[coupled_basin_indices]

        _nullify_ribasim_exchange_input(
            ribasim_component=ribasim_model.basin,
            coupled_node_ids=coupled_basin_node_ids,
            columns=["infiltration", "drainage"],
        )
        return coupling_dict

    def _write_exchange(
        self,
        directory: Path,
        gwf_model: imod.mf6.GroundwaterFlowModel,
        gwf_package_key: str,
        ribasim_model: ribasim.Model,
        basin_ids: pd.Series,
        gridded_basin: xr.DataArray,
    ) -> tuple[str, str, pd.DataFrame]:
        package = gwf_model[gwf_package_key]
        mapping = self.derive_mapping(
            name=gwf_package_key,
            gridded_basin=gridded_basin,
            basin_ids=basin_ids,
            conductance=package["conductance"],
            ribasim_model=ribasim_model,
        )
        if mapping.dataframe.empty:
            raise ValueError(
                f"No coupling can be derived for MODFLOW 6 package: {gwf_package_key}. "
                "No spatial overlap exists between the basin_definition and this package."
            )

        if isinstance(package, imod.mf6.River):
            # Add a MF6 API package for correction flows
            gwf_model["api_" + gwf_package_key] = imod.mf6.ApiPackage(
                maxbound=package._max_active_n(),
                save_flows=True,
            )
            destination = "river"
            #  check if not coupling passive when adding a river package
            if isinstance(self, RibaModPassiveDriverCoupling):
                raise TypeError(
                    f"Expected Drainage packages for passive coupling, received: {type(package).__name__}"
                )

            #  check on the bottom elevation and ribasim minimal subgrid level
            minimum_subgrid_level = (
                ribasim_model.basin.subgrid.df.groupby("subgrid_id")
                .min()["subgrid_level"]
                .to_numpy()
            )
            # in active coupling, check subgrid levels versus modflow bottom elevation
            if isinstance(self, RibaModActiveDriverCoupling):
                subgrid_index = mapping.dataframe["subgrid_index"]
                bound_index = mapping.dataframe["bound_index"]
                bottom_elevation = package["bottom_elevation"].to_numpy()
                if np.any(
                    bottom_elevation[np.isfinite(bottom_elevation)][bound_index]
                    < minimum_subgrid_level[subgrid_index]
                ):
                    index = np.flatnonzero(
                        bottom_elevation[np.isfinite(bottom_elevation)][bound_index]
                        < minimum_subgrid_level[subgrid_index]
                    )
                    values = bound_index[index].to_numpy()
                    raise ValueError(
                        f"Found bottom elevation below minimum subgrid level of Ribasim, for MODFLOW 6 package: {gwf_package_key}, for folowing elements: {values}. "
                    )
        elif isinstance(package, imod.mf6.Drainage):
            destination = "drainage"
        else:
            if isinstance(self, RibaModPassiveDriverCoupling):
                raise TypeError(
                    f"Expected Drainage, received: {type(package).__name__}"
                )
            else:
                raise TypeError(
                    f"Expected River or Drainage, received: {type(package).__name__}"
                )

        filename = mapping.write(directory=directory)
        return filename, destination, mapping.dataframe["basin_index"]


class RibaModActiveDriverCoupling(RibaModDriverCoupling):
    @property
    def _prefix(self) -> str:
        return "active"

    def _validate_subgrid_df(self, ribasim_model: ribasim.Model) -> pd.DataFrame | None:
        if self.mf6_packages:
            if ribasim_model.basin.subgrid.df is None:
                raise ValueError(
                    "ribasim.model.basin.subgrid must be defined for actively coupled packages."
                )
            return ribasim_model.basin.subgrid.df
        else:
            return None

    def derive_mapping(
        self,
        name: str,
        conductance: xr.DataArray,
        gridded_basin: xr.DataArray,
        basin_ids: pd.Series,
        ribasim_model: ribasim.Model,
    ) -> ActiveNodeBasinMapping:
        subgrid_df = self._validate_subgrid_df(ribasim_model)
        return ActiveNodeBasinMapping(
            name=name,
            conductance=conductance,
            gridded_basin=gridded_basin,
            basin_ids=basin_ids,
            subgrid_df=subgrid_df,
        )


class RibaModPassiveDriverCoupling(RibaModDriverCoupling):
    @property
    def _prefix(self) -> str:
        return "passive"

    def derive_mapping(
        self,
        name: str,
        conductance: xr.DataArray,
        gridded_basin: xr.DataArray,
        basin_ids: pd.Series,
        ribasim_model: ribasim.Model,
    ) -> NodeBasinMapping:
        return NodeBasinMapping(
            name=name,
            conductance=conductance,
            gridded_basin=gridded_basin,
            basin_ids=basin_ids,
        )
