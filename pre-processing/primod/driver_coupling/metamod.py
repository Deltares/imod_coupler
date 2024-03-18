from dataclasses import dataclass
from pathlib import Path
from typing import Any

from imod.mf6 import GroundwaterFlowModel, Modflow6Simulation
from imod.msw import GridData

from primod.driver_coupling.driver_coupling_base import DriverCoupling
from primod.mapping.node_svat_mapping import NodeSvatMapping
from primod.mapping.rch_svat_mapping import RechargeSvatMapping
from primod.mapping.wel_svat_mapping import WellSvatMapping


@dataclass
class MetaModDriverCoupling(DriverCoupling):
    """
    Attributes
    ----------
    mf6_model : str
        The model of the driver.
    recharge_package: str
        Key of Modflow 6 recharge package to which MetaSWAP is coupled.
    wel_package: str or None
        Optional key of Modflow 6 well package to which MetaSWAP sprinkling is
        coupled.
    """

    mf6_model: str
    recharge_package: str
    wel_package: str | None = None

    def derive_mapping(
        self, msw_model, gwf_model
    ) -> tuple[NodeSvatMapping, RechargeSvatMapping, WellSvatMapping | None]:
        grid_data_key = [
            pkgname
            for pkgname, pkg in self.msw_model.items()
            if isinstance(pkg, GridData)
        ][0]

        dis = gwf_model[gwf_model._get_pkgkey("dis")]

        index, svat = msw_model[grid_data_key].generate_index_array()
        grid_mapping = NodeSvatMapping(svat, dis)

        recharge = gwf_model[self.recharge_package]

        rch_mapping = RechargeSvatMapping(svat, recharge)

        if self.is_sprinkling:
            well = gwf_model[self.wel_package]
            well_mapping = WellSvatMapping(svat, well)
            return grid_mapping, rch_mapping, well_mapping
        else:
            return grid_mapping, rch_mapping, None

    def _get_gwf_modelnames(self, mf6_simulation: Modflow6Simulation) -> list[str]:
        """
        Get names of gwf models in mf6 simulation
        """
        return [
            key
            for key, value in mf6_simulation.items()
            if isinstance(value, GroundwaterFlowModel)
        ]

    def write_exchanges(self, directory: Path, coupled_model: Any) -> dict[str, Any]:
        mf6_simulation = coupled_model
        gwf_names = self._get_gwf_modelnames(mf6_simulation)
        gwf_name = gwf_names[0]
        gwf_model = mf6_simulation[gwf_name]
        msw_model = coupled_model.msw_model

        grid_mapping, rch_mapping, well_mapping = self.derive_mapping(
            msw_model=msw_model,
            gwf_model=gwf_model,
        )

        coupling_dict: dict[str, Any] = {}
        coupling_dict["mf6_model"] = gwf_name

        coupling_dict["mf6_msw_node_map"] = grid_mapping.write(directory)
        coupling_dict["mf6_msw_recharge_pkg"] = self.recharge_package
        coupling_dict["mf6_msw_recharge_map"] = rch_mapping.write(directory)
        coupling_dict["enable_sprinkling"] = False

        if well_mapping is not None:
            coupling_dict["enable_sprinkling"] = True
            coupling_dict["mf6_msw_well_pkg"] = self.wel_package
            coupling_dict["mf6_msw_sprinkling_map"] = well_mapping.write(directory)

        return coupling_dict


"""
        grid_data_key = [
            pkgname
            for pkgname, pkg in self.msw_model.items()
            if isinstance(pkg, GridData)
        ][0]

        dis = gwf_model[gwf_model._get_pkgkey("dis")]

        index, svat = self.msw_model[grid_data_key].generate_index_array()
        grid_mapping = NodeSvatMapping(svat, dis)
        grid_mapping.write(directory, index, svat)

        recharge = gwf_model[mf6_rch_pkgkey]

        rch_mapping = RechargeSvatMapping(svat, recharge)
        rch_mapping.write(directory, index, svat)

        if self.is_sprinkling:
            well = gwf_model[mf6_wel_pkgkey]
            well_mapping = WellSvatMapping(svat, well)
            well_mapping.write(directory, index, svat)
"""
