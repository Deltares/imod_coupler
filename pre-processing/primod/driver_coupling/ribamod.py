import abc
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import imod
import numpy as np
import pandas as pd
import ribasim
import xarray as xr
from geopandas import gpd
from imod.mf6 import GroundwaterFlowModel
from numpy.typing import Int, NDArray

from primod.driver.util import _validate_node_ids
from primod.driver_coupling.driver_coupling_base import DriverCoupling
from primod.mapping.node_basin_mapping import ActiveNodeBasinMapping, NodeBasinMapping


@dataclass
class RibaModDriverCoupling(DriverCoupling, abc.ABC):
    """A dataclass representing one coupling scenario for the RibaMod driver.

    Attributes
    ----------
    mf6_model: str
        The model of the driver.
    basin_definition : gpd.GeoDataFrame
        GeoDataFrame of basin polygons
    mf6_river_packages : list of str
        A list of river packages.
    mf6_drainage_packages : list of str
        A list of drainage packages.
    """

    mf6_model: str
    basin_definition: gpd.GeoDataFrame
    river_packages: list[str] = field(default_factory=list)
    drainage_packages: list[str] = field(default_factory=list)
    _coupled_basin_node_ids: NDArray[Int] | None = None

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

    def _get_gwf_modelnames(self) -> list[str]:
        """
        Get names of gwf models in mf6 simulation
        """
        return [
            key
            for key, value in self.mf6_simulation.items()
            if isinstance(value, GroundwaterFlowModel)
        ]

    def write_exchanges(
        self,
        directory: Path,
        coupled_model: Any,
    ) -> dict[str, Any]:
        mf6_simulation = coupled_model.mf6_simulation
        gwf_names = self._get_gwf_modelnames(mf6_simulation)
        gwf_model = mf6_simulation[gwf_names[0]]
        ribasim_model = coupled_model

        dis = gwf_model[gwf_model._get_pkgkey("dis")]
        packages = self.asdict()
        packages.pop("mf6_model")
        basin_definition = packages.pop("basin_definition")
        # Validate and fetch
        basin_ids = _validate_node_ids(ribasim_model, basin_definition)

        # Spatial overlays of MF6 boundaries with basin polygons.
        gridded_basin = imod.prepare.rasterize(
            basin_definition,
            like=dis["idomain"].isel(layer=0, drop=True),
            column="node_id",
        )

        # Collect which Ribasim basins are coupled, so that we can set their
        # drainage and infiltration to NoData later on.
        coupling_dict = self._empty_coupling_dict()
        coupled_basin_indices = []
        for destination, keys in packages.items():
            for key in keys:
                package = gwf_model[key]
                # Derive exchange tables
                mapping = self.derive_mapping(
                    name=key,
                    gridded_basin=gridded_basin,
                    basin_ids=basin_ids,
                    conductance=package["conductance"],
                    ribasim_model=ribasim_model,
                )

                if mapping.dataset.empty:
                    raise ValueError(
                        f"No coupling can be derived for MODFLOW 6 package: {key}. "
                        "No spatial overlap exists between the basin_definition and this package."
                    )

                filename = mapping.write(directory=directory)
                coupling_dict[f"mf6_{self._prefix}_{destination}"][key] = filename
                coupled_basin_indices.append(mapping["basin_index"])

        coupled_basin_indices = np.unique(np.concatenate(coupled_basin_indices))
        self._coupled_basin_node_ids = basin_ids[coupled_basin_indices]
        return coupling_dict


@dataclass
class RibaModActiveDriverCoupling(RibaModDriverCoupling):
    @property
    def _prefix(self) -> str:
        return "active"

    def _validate_subgrid_df(self, ribasim_model: ribasim.Model) -> pd.DataFrame | None:
        if self.river_packages or self.drainage_packages:
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


@dataclass
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
