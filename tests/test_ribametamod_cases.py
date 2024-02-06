import ribasim
import xarray as xr
from imod.mf6 import Modflow6Simulation, Recharge
from imod.msw import MetaSwapModel
from primod.ribametamod import DriverCoupling, RibaMetaMod
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


def case_bucket_model(
    mf6_bucket_model: Modflow6Simulation,
    msw_bucket_model: MetaSwapModel,
    ribasim_bucket_model: ribasim.Model,
) -> RibaMetaMod | MetaSwapModel:
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(mf6_bucket_model)[0]
    mf6_active_river_packages = get_mf6_river_packagenames(mf6_model)
    basin_definition = create_basin_definition(ribasim_bucket_model, buffersize=10.0)
    mf6_bucket_model = add_rch_package(mf6_bucket_model)

    driver_coupling = DriverCoupling(
        mf6_model=mf6_modelname,
        mf6_active_river_packages=mf6_active_river_packages,
    )
    # should becomde RibaMetaMod-class, including the MetaSWAP model
    return RibaMetaMod(
        ribasim_model=ribasim_bucket_model,
        mf6_simulation=mf6_bucket_model,
        basin_definition=basin_definition,
        coupling_list=[driver_coupling],
    ), msw_bucket_model


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

    driver_coupling = DriverCoupling(
        mf6_model=mf6_modelname,
        mf6_active_river_packages=mf6_active_river_packages,
        mf6_active_drainage_packages=mf6_active_drainage_packages,
    )
    # should becomde RibaMetaMod-class, including the MetaSWAP model
    return RibaMetaMod(
        ribasim_model=ribasim_backwater_model,
        mf6_simulation=mf6_backwater_model,
        basin_definition=basin_definition,
        coupling_list=[driver_coupling],
    ), msw_backwater_model


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
    driver_coupling = DriverCoupling(
        mf6_model=mf6_modelname,
        mf6_active_river_packages=mf6_active_river_packages,
    )
    # should becomde RibaMetaMod-class, including the MetaSWAP model
    return RibaMetaMod(
        ribasim_model=ribasim_two_basin_model,
        mf6_simulation=mf6_two_basin_model,
        basin_definition=basin_definition,
        coupling_list=[driver_coupling],
    ), msw_two_basin_model
