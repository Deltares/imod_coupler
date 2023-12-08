import geopandas as gpd
import ribasim
from imod.mf6 import Drainage, GroundwaterFlowModel, Modflow6Simulation, River
from primod.ribamod import DriverCoupling, RibaMod


# test this function!
def create_basin_definition(
    ribasim_model: ribasim.Model, buffersize: float
) -> gpd.GeoDataFrame:
    node = ribasim_model.network.node.df
    basin_nodes = ribasim_model.basin.static.df["node_id"].unique()
    basin_geometry = node.loc[basin_nodes].geometry
    # Call to_numpy() to get rid of the index
    basin_definition = gpd.GeoDataFrame(
        data={"node_id": basin_nodes},
        geometry=basin_geometry.buffer(buffersize).to_numpy(),
    )
    return basin_definition


def case_bucket_model(
    mf6_bucket_model: Modflow6Simulation,
    ribasim_bucket_model: ribasim.Model,
) -> RibaMod:
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(mf6_bucket_model)[0]
    mf6_active_river_packages = get_mf6_river_packagenames(mf6_model)

    basin_definition = create_basin_definition(ribasim_bucket_model, buffersize=10.0)

    driver_coupling = DriverCoupling(
        mf6_model=mf6_modelname,
        mf6_active_river_packages=mf6_active_river_packages,
    )

    return RibaMod(
        ribasim_model=ribasim_bucket_model,
        mf6_simulation=mf6_bucket_model,
        basin_definition=basin_definition,
        coupling_list=[driver_coupling],
    )


def case_backwater_model(
    mf6_backwater_model: Modflow6Simulation,
    ribasim_backwater_model: ribasim.Model,
) -> RibaMod:
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(mf6_backwater_model)[0]
    mf6_active_river_packages = get_mf6_river_packagenames(mf6_model)
    mf6_active_drainage_packages = get_mf6_drainage_packagenames(mf6_model)

    basin_definition = create_basin_definition(ribasim_backwater_model, buffersize=5.0)

    driver_coupling = DriverCoupling(
        mf6_model=mf6_modelname,
        mf6_active_river_packages=mf6_active_river_packages,
        mf6_active_drainage_packages=mf6_active_drainage_packages,
    )

    return RibaMod(
        ribasim_model=ribasim_backwater_model,
        mf6_simulation=mf6_backwater_model,
        basin_definition=basin_definition,
        coupling_list=[driver_coupling],
    )


def case_two_basin_model(
    mf6_two_basin_model: Modflow6Simulation,
    ribasim_two_basin_model: ribasim.Model,
) -> RibaMod:
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(mf6_two_basin_model)[0]
    mf6_active_river_packages = get_mf6_river_packagenames(mf6_model)

    basin_definition = create_basin_definition(
        ribasim_two_basin_model, buffersize=250.0
    )

    driver_coupling = DriverCoupling(
        mf6_model=mf6_modelname,
        mf6_active_river_packages=mf6_active_river_packages,
    )

    return RibaMod(
        ribasim_model=ribasim_two_basin_model,
        mf6_simulation=mf6_two_basin_model,
        basin_definition=basin_definition,
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
