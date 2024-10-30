import copy
from pathlib import Path
from typing import Any

import geopandas as gpd
import imod
import numpy as np
import ribasim
import xarray as xr
from imod.msw import GridData, MetaSwapModel, Sprinkling

from primod.driver_coupling.driver_coupling_base import DriverCoupling
from primod.driver_coupling.util import (
    _nullify_ribasim_exchange_input,
    _validate_node_ids,
)
from primod.mapping.svat_basin_mapping import SvatBasinMapping
from primod.mapping.svat_user_demand_mapping import SvatUserDemandMapping


class RibaMetaDriverCoupling(DriverCoupling):
    """A dataclass representing one coupling scenario for the RibaMod driver.

    Attributes
    ----------
    basin_definition: gpd.GeoDataFrame | xr.DataArray
        GeoDataFrame of basin polygons or xr.DataArray with gridded basin nodes
    user_demand_definition: gpd.GeoDataFrame| xr.DataArray
        GeoDataFrame of user demand polygons or xr.DataArray with gridded demand nodes
    """

    ribasim_basin_definition: gpd.GeoDataFrame | xr.DataArray
    ribasim_user_demand_definition: gpd.GeoDataFrame | xr.DataArray | None = None

    def _check_sprinkling(self, msw_model: MetaSwapModel) -> bool:
        sprinkling_key = msw_model._get_pkg_key(Sprinkling, optional_package=True)
        sprinkling_in_msw = sprinkling_key is not None
        sprinkling_in_ribasim = self.ribasim_user_demand_definition is not None

        if sprinkling_in_ribasim:
            if sprinkling_in_msw:
                return True
            else:
                raise ValueError(
                    "Ribasim UserDemand definition provided, "
                    "but no Sprinkling package found in MetaSWAP model."
                )
        else:
            return False

    def derive_mapping(
        self,
        ribasim_model: ribasim.Model,
        msw_model: MetaSwapModel,
    ) -> tuple[SvatBasinMapping, SvatUserDemandMapping | None]:
        grid_data_key = [
            pkgname for pkgname, pkg in msw_model.items() if isinstance(pkg, GridData)
        ][0]

        index, svat = msw_model[grid_data_key].generate_index_array()
        basin_ids = _validate_node_ids(
            ribasim_model.basin.node.df, self.ribasim_basin_definition
        )
        if isinstance(self.ribasim_basin_definition, gpd.GeoDataFrame):
            gridded_basin = imod.prepare.rasterize(
                self.ribasim_basin_definition,
                like=svat.isel(subunit=0, drop=True),
                column="node_id",
                dtype=np.float64,
            )
        elif isinstance(self.ribasim_basin_definition, xr.DataArray):
            gridded_basin = self.ribasim_basin_definition
        else:
            raise TypeError(
                "Expected geopandas.GeoDataFrame or xr.Dataset: "
                f"received {type(self.ribasim_basin_definition.__name__)}"
            )
        svat_basin_mapping = SvatBasinMapping(
            name="msw_ponding",
            gridded_basin=gridded_basin,
            basin_ids=basin_ids,
            svat=svat,
            index=index,
        )

        if self._check_sprinkling(msw_model=msw_model):
            user_demand_ids = _validate_node_ids(
                ribasim_model.user_demand.node.df, self.ribasim_user_demand_definition
            )
            if isinstance(self.ribasim_user_demand_definition, gpd.GeoDataFrame):
                gridded_user_demand = imod.prepare.rasterize(
                    self.ribasim_user_demand_definition,
                    like=svat.isel(subunit=0, drop=True),
                    column="node_id",
                    dtype=np.float64,
                )
            elif isinstance(self.ribasim_user_demand_definition, xr.DataArray):
                gridded_user_demand = self.ribasim_user_demand_definition
            else:
                raise TypeError(
                    "Expected geopandas.GeoDataFrame or xr.Dataset: "
                    f"received {type(self.ribasim_user_demand_definition.__name__)}"  # type: ignore
                )
            # sprinkling surface water for subsection of svats determined in 'sprinkling'
            swspr_grid_data = copy.deepcopy(msw_model[grid_data_key])
            nsu = swspr_grid_data.dataset["area"].sizes["subunit"]
            swsprmax = msw_model["sprinkling"]
            swspr_grid_data.dataset["area"].values = np.tile(
                swsprmax["max_abstraction_surfacewater_m3_d"].values,
                (nsu, 1, 1),
            )
            index_swspr, svat_swspr = swspr_grid_data.generate_index_array()
            svat_user_demand_mapping = SvatUserDemandMapping(
                name="msw_sw_sprinkling",
                gridded_user_demand=gridded_user_demand,
                user_demand_ids=user_demand_ids,
                svat=svat_swspr,
                index=index_swspr,
            )
            return svat_basin_mapping, svat_user_demand_mapping
        else:
            return svat_basin_mapping, None

    def write_exchanges(self, directory: Path, coupled_model: Any) -> dict[str, Any]:
        ribasim_model = coupled_model.ribasim_model
        msw_model = coupled_model.msw_model

        svat_basin_mapping, svat_user_demand_mapping = self.derive_mapping(
            ribasim_model=ribasim_model,
            msw_model=msw_model,
        )

        coupling_dict: dict[str, Any] = {}
        coupling_dict["rib_msw_ponding_map_surface_water"] = svat_basin_mapping.write(
            directory=directory
        )

        # Set Ribasim runoff input to Null for coupled basins
        basin_ids = _validate_node_ids(
            ribasim_model.basin.node.df, self.ribasim_basin_definition
        )
        coupled_basin_indices = svat_basin_mapping.dataframe["basin_index"]
        coupled_basin_node_ids = basin_ids[coupled_basin_indices]
        _nullify_ribasim_exchange_input(
            ribasim_component=ribasim_model.basin,
            coupled_node_ids=coupled_basin_node_ids,
            columns=["runoff"],
        )

        # Now deal with sprinkling if set
        if svat_user_demand_mapping is not None:
            _ = _validate_node_ids(
                ribasim_model.user_demand.node.df, self.ribasim_user_demand_definition
            )
            coupling_dict["rib_msw_sprinkling_map_surface_water"] = (
                svat_user_demand_mapping.write(directory=directory)
            )
        return coupling_dict
