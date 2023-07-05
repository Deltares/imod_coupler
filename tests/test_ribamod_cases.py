import ribasim
from imod.couplers.ribamod import DriverCoupling, RibaMod
from imod.mf6 import GroundwaterFlowModel, Modflow6Simulation, River


def case_trivial_model(
    coupled_ribasim_mf6_model: Modflow6Simulation,
    ribasim_model: ribasim.Model,
) -> RibaMod:
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(coupled_ribasim_mf6_model)[0]
    mf6_river_packages = get_mf6_river_packagenames(mf6_model)

    driver_coupling = DriverCoupling(
        mf6_model=mf6_modelname,
        mf6_river_packages=mf6_river_packages,
        mf6_drainage_packages=[],
    )

    return RibaMod(
        ribasim_model=ribasim_model,
        mf6_simulation=coupled_ribasim_mf6_model,
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
