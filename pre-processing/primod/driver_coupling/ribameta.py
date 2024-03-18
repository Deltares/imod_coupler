from pathlib import Path
from typing import Any

import imod
import ribasim
import xarray as xr

from primod.driver_coupling.driver_coupling_base import DriverCoupling
from primod.driver_coupling.util import _validate_node_ids


@dataclass
class RibaMetaDriverCoupling(DriverCoupling):
    """A dataclass representing one coupling scenario for the RibaMod driver.

    Attributes
    ----------
    basin_definition: gpd.GeoDataFrame
        GeoDataFrame of basin polygons
    userdemand_definition: gpd.GeoDataFrame
        GeoDataFrame of user demand polygons
    """

    def derive_mapping(
        self,
        ribasim_model: ribasim.Model,
        msw_model: xr.DataArray,
    ):
        basin_ids = _validate_node_ids(ribasim_model, self.basin_definition)
        userdemand_ids = _validate_node_ids(ribasim_model, self.userdemand_definition)
        gridded_basin = imod.prepare.rasterize(
            self.basin_definition,
            like=svat,
            column="node_id",
        )
        gridded_userdemand = imod.prepare.rasterize(
            self.basin_definition,
            like=svat,
            column="node_id",
        )

        svat_basin_mapping = SvatBasinMapping(
            name="msw_ponding",
            gridded_basin=gridded_basin,
            basin_ids=basin_ids,
            condition=svat > 0,
        )
        svat_userdemand_mapping = SvatBasinMapping(
            name="msw_sw_sprinkling",
            gridded_basin=gridded_userdemand,
            basin_ids=userdemand_ids,
            condition=svat_swspr.notnull(),
        )
        return svat_basin_mapping, svat_userdemand_mapping

    def write_exchanges(self, directory: Path, coupled_model: Any) -> dict[str, Any]:
        ribasim_model = coupled_model.ribasim_model
        msw_model = coupled_model.msw_model

        svat_basin_mapping, svat_userdemand_mapping = self.derive_mapping(
            ribasim_model=ribasim_model,
            msw_model=msw_model,
        )

        coupling_dict: dict[str, Any] = {}
        coupling_dict["rib_msw_ponding_map_surface_water"] = svat_basin_mapping.write(
            directory=directory
        )
        coupling_dict["rib_msw_sprinkling_map_surface_water"] = (
            svat_userdemand_mapping.write(directory=directory)
        )
        return coupling_dict
