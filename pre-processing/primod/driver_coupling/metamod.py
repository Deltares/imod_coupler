from pathlib import Path
from typing import Any

from imod.mf6 import GroundwaterFlowModel
from imod.msw import GridData, MetaSwapModel, Sprinkling

from primod.driver_coupling.driver_coupling_base import DriverCoupling
from primod.driver_coupling.util import _get_gwf_modelnames
from primod.mapping.node_svat_mapping import NodeSvatMapping
from primod.mapping.rch_svat_mapping import RechargeSvatMapping
from primod.mapping.wel_svat_mapping import WellSvatMapping


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

    def _check_keys(
        self, msw_model: MetaSwapModel, gwf_model: GroundwaterFlowModel
    ) -> bool:
        sprinkling_key = msw_model._get_pkg_key(Sprinkling, optional_package=True)
        sprinkling_in_msw = sprinkling_key is not None
        sprinkling_in_mf6 = self.wel_package in gwf_model.keys()

        if sprinkling_in_msw and not sprinkling_in_mf6:
            raise ValueError(
                f"No package named {self.wel_package} found in Modflow 6 model, "
                "but Sprinkling package found in MetaSWAP. "
                "iMOD Coupler requires a Well Package "
                "to couple wells."
            )
        elif not sprinkling_in_msw and sprinkling_in_mf6:
            raise ValueError(
                f"Modflow 6 Well package {self.wel_package} specified for sprinkling, "
                "but no Sprinkling package found in MetaSWAP model."
            )
        elif sprinkling_in_msw and sprinkling_in_mf6:
            return True
        else:
            return False

    def derive_mapping(
        self, msw_model: MetaSwapModel, gwf_model: GroundwaterFlowModel
    ) -> tuple[NodeSvatMapping, RechargeSvatMapping, WellSvatMapping | None]:
        if self.recharge_package not in gwf_model.keys():
            raise ValueError(
                f"No package named {self.recharge_package} detected in Modflow 6 model. "
                "iMOD_coupler requires a Recharge package."
            )

        grid_data_key = [
            pkgname for pkgname, pkg in msw_model.items() if isinstance(pkg, GridData)
        ][0]

        dis = gwf_model[gwf_model._get_pkgkey("dis")]

        index, svat = msw_model[grid_data_key].generate_index_array()
        grid_mapping = NodeSvatMapping(svat, dis)

        recharge = gwf_model[self.recharge_package]

        rch_mapping = RechargeSvatMapping(svat, recharge)

        if self._check_sprinking(msw_model=msw_model, gwf_model=gwf_model):
            well = gwf_model[self.wel_package]
            well_mapping = WellSvatMapping(svat, well)
            return grid_mapping, rch_mapping, well_mapping
        else:
            return grid_mapping, rch_mapping, None

    def write_exchanges(self, directory: Path, coupled_model: Any) -> dict[str, Any]:
        mf6_simulation = coupled_model
        gwf_names = _get_gwf_modelnames(mf6_simulation)
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
