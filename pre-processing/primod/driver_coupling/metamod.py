from pathlib import Path
from typing import Any

from imod.mf6 import GroundwaterFlowModel
from imod.msw import GridData, MetaSwapModel, Sprinkling

from primod.driver_coupling.driver_coupling_base import DriverCoupling
from primod.mapping.node_svat_mapping import NodeSvatMapping
from primod.mapping.rch_svat_mapping import RechargeSvatMapping
from primod.mapping.wel_svat_mapping import WellSvatMapping


class MetaModDriverCoupling(DriverCoupling):
    """
    Attributes
    ----------
    mf6_model : str
        The model of the driver.
    mf6_recharge_package: str
        Key of Modflow 6 recharge package to which MetaSWAP is coupled.
    mf6_wel_package: str or None
        Optional key of Modflow 6 well package to which MetaSWAP sprinkling is
        coupled.
    """

    mf6_model: str
    mf6_recharge_package: str
    mf6_wel_package: str | None = None

    def _check_sprinkling(
        self, msw_model: MetaSwapModel, gwf_model: GroundwaterFlowModel
    ) -> bool:
        sprinkling_key = msw_model.get_pkgkey(Sprinkling, optional_package=True)
        sprinkling_in_msw = sprinkling_key is not None
        sprinkling_in_mf6 = self.mf6_wel_package in gwf_model.keys()

        value = False
        match (sprinkling_in_msw, sprinkling_in_mf6):
            case (True, False):
                raise ValueError(
                    f"No package named {self.mf6_wel_package} found in Modflow 6 model, "
                    "but Sprinkling package found in MetaSWAP. "
                    "iMOD Coupler requires a Well Package "
                    "to couple wells."
                )
            case (False, True):
                raise ValueError(
                    f"Modflow 6 Well package {self.mf6_wel_package} specified for sprinkling, "
                    "but no Sprinkling package found in MetaSWAP model."
                )
            case (True, True):
                value = True
            case (False, False):
                value = False

        return value

    def derive_mapping(
        self, msw_model: MetaSwapModel, gwf_model: GroundwaterFlowModel
    ) -> tuple[NodeSvatMapping, RechargeSvatMapping, WellSvatMapping | None]:
        if self.mf6_recharge_package not in gwf_model.keys():
            raise ValueError(
                f"No package named {self.mf6_recharge_package} detected in Modflow 6 model. "
                "iMOD_coupler requires a Recharge package."
            )

        grid_data_key = [
            pkgname for pkgname, pkg in msw_model.items() if isinstance(pkg, GridData)
        ][0]

        dis = gwf_model[gwf_model.get_diskey()]

        index, svat = msw_model[grid_data_key].generate_index_array()
        grid_mapping = NodeSvatMapping(svat=svat, modflow_dis=dis, index=index)

        recharge = gwf_model[self.mf6_recharge_package]

        rch_mapping = RechargeSvatMapping(svat, recharge, index=index)

        if self._check_sprinkling(msw_model=msw_model, gwf_model=gwf_model):
            well = gwf_model.prepare_wel_for_mf6(self.mf6_wel_package, True, True)
            well_mapping = WellSvatMapping(svat, well, index=index)
            return grid_mapping, rch_mapping, well_mapping
        else:
            return grid_mapping, rch_mapping, None

    def write_exchanges(self, directory: Path, coupled_model: Any) -> dict[str, Any]:
        mf6_simulation = coupled_model.mf6_simulation
        gwf_model = mf6_simulation[self.mf6_model]
        msw_model = coupled_model.msw_model

        grid_mapping, rch_mapping, well_mapping = self.derive_mapping(
            msw_model=msw_model,
            gwf_model=gwf_model,
        )

        coupling_dict: dict[str, Any] = {}
        coupling_dict["mf6_model"] = self.mf6_model

        coupling_dict["mf6_msw_node_map"] = grid_mapping.write(directory)
        coupling_dict["mf6_msw_recharge_pkg"] = self.mf6_recharge_package
        coupling_dict["mf6_msw_recharge_map"] = rch_mapping.write(directory)

        if well_mapping is not None:
            coupling_dict["mf6_msw_well_pkg"] = self.mf6_wel_package
            coupling_dict["mf6_msw_sprinkling_map_groundwater"] = well_mapping.write(
                directory
            )

        return coupling_dict
