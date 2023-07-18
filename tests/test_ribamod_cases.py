import ribasim
from imod.couplers.ribamod import DriverCoupling, RibaMod
from imod.mf6 import Drainage, GroundwaterFlowModel, Modflow6Simulation, River


def case_bucket_model(
    mf6_bucket_model: Modflow6Simulation,
    ribasim_bucket_model: ribasim.Model,
) -> RibaMod:
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(mf6_bucket_model)[0]
    mf6_river_packages = get_mf6_river_packagenames(mf6_model)

    driver_coupling = DriverCoupling(
        mf6_model=mf6_modelname,
        mf6_river_packages=mf6_river_packages,
        mf6_drainage_packages=[],
    )

    return RibaMod(
        ribasim_model=ribasim_bucket_model,
        mf6_simulation=mf6_bucket_model,
        coupling_list=[driver_coupling],
    )


def case_backwater_model(
    mf6_backwater_model: Modflow6Simulation,
    ribasim_backwater_model: ribasim.Model,
) -> RibaMod:
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(mf6_backwater_model)[0]
    mf6_river_packages = get_mf6_river_packagenames(mf6_model)
    mf6_drainage_packages = get_mf6_drainage_packagenames(mf6_model)

    driver_coupling = DriverCoupling(
        mf6_model=mf6_modelname,
        mf6_river_packages=mf6_river_packages,
        mf6_drainage_packages=mf6_drainage_packages,
    )

    return RibaMod(
        ribasim_model=ribasim_backwater_model,
        mf6_simulation=mf6_backwater_model,
        coupling_list=[driver_coupling],
    )


def get_mf6_gwf_modelnames(
    mf6_simulation: Modflow6Simulation,
) -> list[tuple[str, GroundwaterFlowModel]]:
    """
    Get names of gwf models in mf6 simulation
    """
    return [
        (key, value)
        for key, value in mf6_simulation.items()
        if isinstance(value, GroundwaterFlowModel)
    ]


def get_mf6_river_packagenames(mf6_model: GroundwaterFlowModel) -> list[str]:
    """
    Get names of river packages in mf6 simulation
    """
    return [key for key, value in mf6_model.items() if isinstance(value, River)]


def get_mf6_drainage_packagenames(mf6_model: GroundwaterFlowModel) -> list[str]:
    """
    Get names of river packages in mf6 simulation
    """
    return [key for key, value in mf6_model.items() if isinstance(value, Drainage)]
