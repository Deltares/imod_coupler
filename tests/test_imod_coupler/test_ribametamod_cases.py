import geopandas as gpd
import ribasim
import xarray as xr
from fixtures.common import create_wells_max_layer
from imod import msw
from imod.mf6 import Modflow6Simulation, Recharge, StorageCoefficient
from imod.msw import MetaSwapModel
from primod import (
    MetaModDriverCoupling,
    RibaMetaDriverCoupling,
    RibaMetaMod,
    RibaModActiveDriverCoupling,
)
from test_ribamod_cases import (
    create_basin_definition,
    get_mf6_drainage_packagenames,
    get_mf6_gwf_modelnames,
    get_mf6_river_packagenames,
)


def add_rch_package(
    mf6_model: Modflow6Simulation,
) -> Modflow6Simulation:
    """
    adds recharge package to MODFLOW6 model for coupling with MetaSWAP
    """
    idomain = mf6_model["GWF_1"]["dis"]["idomain"]
    recharge = xr.zeros_like(idomain.sel(layer=1), dtype=float)
    recharge = recharge.where(idomain.sel(layer=1))
    mf6_model["GWF_1"]["rch_msw"] = Recharge(rate=recharge)
    return mf6_model


def add_well_package(
    mf6_model: Modflow6Simulation,
) -> Modflow6Simulation:
    idomain = mf6_model["GWF_1"]["dis"]["idomain"]
    _, nrow, ncol = idomain.shape
    mf6_model["GWF_1"]["well_msw"] = create_wells_max_layer(nrow, ncol, idomain)
    return mf6_model


def case_bucket_model(
    mf6_bucket_model: Modflow6Simulation,
    msw_bucket_model: MetaSwapModel,
    ribasim_bucket_model: ribasim.Model,
) -> RibaMetaMod:
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(mf6_bucket_model)[0]
    mf6_active_river_packages = get_mf6_river_packagenames(mf6_model)
    basin_definition = create_basin_definition(ribasim_bucket_model, buffersize=100.0)
    mf6_bucket_model = add_rch_package(mf6_bucket_model)
    mf6_bucket_model = add_well_package(mf6_bucket_model)

    metamod_coupling = MetaModDriverCoupling(
        mf6_model=mf6_modelname,
        mf6_recharge_package="rch_msw",
        mf6_wel_package="well_msw",
    )
    ribamod_coupling = RibaModActiveDriverCoupling(
        mf6_model=mf6_modelname,
        mf6_packages=mf6_active_river_packages,
        ribasim_basin_definition=basin_definition,
    )
    ribameta_coupling = RibaMetaDriverCoupling(
        ribasim_basin_definition=basin_definition,
    )
    # increase resistance to 1 day
    conductance = mf6_bucket_model["GWF_1"][mf6_active_river_packages[0]].dataset[
        "conductance"
    ]
    conductance = conductance / 400
    mf6_bucket_model["GWF_1"][mf6_active_river_packages[0]].dataset["conductance"] = (
        conductance
    )
    mf6_bucket_model["GWF_1"].pop("sto")
    bottom = mf6_bucket_model["GWF_1"]["dis"]["bottom"]
    ss = xr.ones_like(bottom) * 1e-6
    ss[0, :, :] = 0.15  # phreatic layer, importent for non coupled nodes
    mf6_bucket_model["GWF_1"]["sto"] = StorageCoefficient(ss, 0.1, True, 0)

    return RibaMetaMod(
        ribasim_model=ribasim_bucket_model,
        msw_model=msw_bucket_model,
        mf6_simulation=mf6_bucket_model,
        coupling_list=[metamod_coupling, ribamod_coupling, ribameta_coupling],
    )


def case_backwater_model(
    mf6_backwater_model: Modflow6Simulation,
    msw_backwater_model: MetaSwapModel,
    ribasim_backwater_model: ribasim.Model,
) -> RibaMetaMod | MetaSwapModel:
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(mf6_backwater_model)[0]
    mf6_active_river_packages = get_mf6_river_packagenames(mf6_model)
    mf6_active_drainage_packages = get_mf6_drainage_packagenames(mf6_backwater_model)
    basin_definition = create_basin_definition(ribasim_backwater_model, buffersize=5.0)
    mf6_backwater_model = add_rch_package(mf6_backwater_model)
    mf6_backwater_model = add_well_package(mf6_backwater_model)

    mf6_backwater_model["GWF_1"]

    metamod_coupling = MetaModDriverCoupling(
        mf6_model=mf6_modelname,
        mf6_recharge_package="rch_msw",
        mf6_wel_package="well_msw",
    )
    ribamod_coupling = RibaModActiveDriverCoupling(
        mf6_model=mf6_modelname,
        mf6_packages=mf6_active_river_packages + mf6_active_drainage_packages,
        ribasim_basin_definition=basin_definition,
    )
    ribameta_coupling = RibaMetaDriverCoupling(
        ribasim_basin_definition=basin_definition,
    )
    return RibaMetaMod(
        ribasim_model=ribasim_backwater_model,
        msw_model=msw_backwater_model,
        mf6_simulation=mf6_backwater_model,
        coupling_list=[metamod_coupling, ribamod_coupling, ribameta_coupling],
    )


def case_two_basin_model(
    mf6_two_basin_model: Modflow6Simulation,
    msw_two_basin_model: MetaSwapModel,
    ribasim_two_basin_model: ribasim.Model,
) -> RibaMetaMod | MetaSwapModel:
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(mf6_two_basin_model)[0]
    mf6_active_river_packages = get_mf6_river_packagenames(mf6_model)
    basin_definition = create_basin_definition(
        ribasim_two_basin_model, buffersize=250.0
    )
    mf6_two_basin_model = add_rch_package(mf6_two_basin_model)
    mf6_two_basin_model = add_well_package(mf6_two_basin_model)

    msw_two_basin_model.pop("sprinkling")
    msw_two_basin_model.pop("mod2svat")
    msw_two_basin_model["mod2svat"] = msw.CouplerMapping(
        modflow_dis=mf6_two_basin_model["GWF_1"]["dis"]
    )

    mf6_two_basin_model["GWF_1"].pop("sto")
    idomain = mf6_two_basin_model["GWF_1"]["dis"]["idomain"]
    ss = xr.ones_like(idomain, dtype=float) * 1e-6
    ss[0, :, :] = 0.15  # phreatic layer, importent for non coupled nodes
    mf6_two_basin_model["GWF_1"]["sto"] = StorageCoefficient(ss, 0.1, True, 0)

    metamod_coupling = MetaModDriverCoupling(
        mf6_model=mf6_modelname,
        mf6_recharge_package="rch_msw",
    )  #         mf6_wel_package="well_msw",
    ribamod_coupling = RibaModActiveDriverCoupling(
        mf6_model=mf6_modelname,
        mf6_packages=mf6_active_river_packages,
        ribasim_basin_definition=basin_definition,
    )
    ribameta_coupling = RibaMetaDriverCoupling(
        ribasim_basin_definition=basin_definition,
    )

    return RibaMetaMod(
        ribasim_model=ribasim_two_basin_model,
        msw_model=msw_two_basin_model,
        mf6_simulation=mf6_two_basin_model,
        coupling_list=[metamod_coupling, ribamod_coupling, ribameta_coupling],
    )
