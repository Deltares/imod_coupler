from pathlib import Path
from typing import Any

import xarray as xr
from imod import mf6
from imod.mf6 import GroundwaterFlowModel, Modflow6Simulation
from imod.msw import GridData, MetaSwapModel, Sprinkling

from primod.driver_coupling.driver_coupling_base import DriverCoupling
from primod.mapping.node_max_layer import ModMaxLayer
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
    mf6_max_layer: xr.DataArray | None = None

    def has_newton_formulation(self, mf6_simulation: Modflow6Simulation) -> bool:
        has_newton = bool(mf6_simulation[self.mf6_model]._options["newton"])
        if has_newton:
            self._check_newton_simulation_settings(mf6_simulation[self.mf6_model])
        return has_newton

    def _check_newton_simulation_settings(
        self, gwf_model: GroundwaterFlowModel
    ) -> None:
        # check if both npf-package and sto-package are convertible since npf-sat is used in coupling
        # and SY is used as exchange variable
        idomain = get_idomain(gwf_model)
        if idomain is None:
            raise ValueError("Could not find idomain in Modflow 6 model")
        mask = xr.ones_like(idomain)
        for label in gwf_model:
            package = gwf_model[label]
            if isinstance(package, mf6.NodePropertyFlow):
                # broadcast (layered) constants
                npf_celtype = (mask * gwf_model[label].dataset["icelltype"]) > 0
            if isinstance(package, mf6.SpecificStorage) or isinstance(
                package, mf6.StorageCoefficient
            ):
                # broadcast (layered) constants
                sto_celtype = (mask * gwf_model[label].dataset["convertible"]) > 0
        if not (npf_celtype & sto_celtype).any():
            raise ValueError("Celtype need to be equal for both NPF and STO package ")

        # Check is fixed_cell option is defined for rch-package
        if "fixed_cell" not in gwf_model[self.mf6_recharge_package].dataset.var():
            raise ValueError(
                f"Option 'fixed_cell' is obligatory for {self.mf6_recharge_package} package, "
                "when using the 'modflow_newton_formulation' of MetaMod driver"
            )
        # Check if well-nodes are non-convertible
        if self.mf6_wel_package is not None:
            ilayer = gwf_model[self.mf6_wel_package].dataset["layer"] - 1
            irow = gwf_model[self.mf6_wel_package].dataset["row"] - 1
            icolumn = gwf_model[self.mf6_wel_package].dataset["column"] - 1
            for label in gwf_model:
                package = gwf_model[label]
                if isinstance(package, mf6.NodePropertyFlow):
                    iceltype = mask * package.dataset["icelltype"]
                    convertible = (iceltype[ilayer, irow, icolumn] != 0).any()
                    if convertible:
                        raise ValueError(
                            "Found convertible cells with irrigation extraction assigned to them"
                        )

    def _check_sprinkling(
        self, msw_model: MetaSwapModel, gwf_model: GroundwaterFlowModel
    ) -> bool:
        sprinkling_key = msw_model._get_pkg_key(Sprinkling, optional_package=True)
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
    ) -> tuple[
        NodeSvatMapping, RechargeSvatMapping, WellSvatMapping | None, ModMaxLayer | None
    ]:
        if self.mf6_recharge_package not in gwf_model.keys():
            raise ValueError(
                f"No package named {self.mf6_recharge_package} detected in Modflow 6 model. "
                "iMOD_coupler requires a Recharge package."
            )

        grid_data_key = [
            pkgname for pkgname, pkg in msw_model.items() if isinstance(pkg, GridData)
        ][0]

        dis = gwf_model[gwf_model._get_pkgkey("dis")]

        index, svat = msw_model[grid_data_key].generate_index_array()
        grid_mapping = NodeSvatMapping(svat=svat, modflow_dis=dis, index=index)

        max_layer = None
        if self.mf6_max_layer is not None:
            max_layer = ModMaxLayer(grid_mapping["mod_id"], self.mf6_max_layer)

        recharge = gwf_model[self.mf6_recharge_package]

        rch_mapping = RechargeSvatMapping(svat, recharge, index=index)

        well_mapping = None
        if self._check_sprinkling(msw_model=msw_model, gwf_model=gwf_model):
            pass
            # well = gwf_model[self.mf6_wel_package]
            # well_mapping = WellSvatMapping(svat, well, index=index)

        return grid_mapping, rch_mapping, well_mapping, max_layer

    def write_exchanges(self, directory: Path, coupled_model: Any) -> dict[str, Any]:
        mf6_simulation = coupled_model.mf6_simulation
        gwf_model = mf6_simulation[self.mf6_model]
        msw_model = coupled_model.msw_model

        grid_mapping, rch_mapping, well_mapping, max_layer = self.derive_mapping(
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
        if max_layer is not None:
            coupling_dict["mf6_node_max_layer"] = max_layer.write(directory)
        return coupling_dict


def get_idomain(gwf_model: GroundwaterFlowModel) -> xr.DataArray | None:
    idomain: xr.DataArray | None = None
    for label in gwf_model:
        package = gwf_model[label]
        if isinstance(package, mf6.StructuredDiscretization):
            idomain = gwf_model[label].dataset["idomain"]
    return idomain
