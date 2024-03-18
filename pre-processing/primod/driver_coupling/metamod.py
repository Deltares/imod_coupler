from dataclasses import dataclass

from imod.mf6 import GroundwaterFlowModel
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

    def process(
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

    def _get_gwf_modelnames(self) -> list[str]:
        """
        Get names of gwf models in mf6 simulation
        """
        return [
            key
            for key, value in self.mf6_simulation.items()
            if isinstance(value, GroundwaterFlowModel)
        ]
