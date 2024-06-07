import geopandas as gpd
import numpy as np
import ribasim
import ribasim.geometry
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
from ribasim.geometry import NodeTable as RibaNodeTbl
from ribasim.nodes import user_demand
from shapely.geometry import Point
from test_ribamod_cases import (
    get_mf6_drainage_packagenames,
    get_mf6_gwf_modelnames,
    get_mf6_river_packagenames,
)


def create_basin_definition(
    node: RibaNodeTbl,
    buffersize: float,
    yoff: float = 0.0,
    xoff: float = 0.0,
    **kwargs,
) -> gpd.GeoDataFrame:
    # Call to_numpy() to get rid of the index
    nodelist: list[int]
    if "nodes" in kwargs:
        nodelist = kwargs["nodes"]
    else:
        nodelist = list(node.df["node_id"])
    sel = node.df["node_id"].isin(nodelist)
    basin_definition = gpd.GeoDataFrame(
        data={"node_id": node.df.loc[sel]["node_id"].to_numpy()},
        geometry=node.df[sel]["geometry"]
        .translate(yoff=yoff, xoff=xoff)
        .buffer(buffersize)
        .to_numpy(),
    )
    return basin_definition


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
    basin_definition = create_basin_definition(
        ribasim_bucket_model.basin.node, buffersize=100.0
    )
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
    idomain = mf6_bucket_model["GWF_1"]["dis"]["idomain"]
    ss = xr.ones_like(idomain) * 1e-6
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
) -> RibaMetaMod:
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(mf6_backwater_model)[0]
    mf6_active_river_packages = get_mf6_river_packagenames(mf6_model)
    mf6_active_drainage_packages = get_mf6_drainage_packagenames(mf6_backwater_model)
    basin_definition = create_basin_definition(
        ribasim_backwater_model.basin.node,
        buffersize=5.0,
    )
    # offset basin definition by one node, since no svats are defined at river nodes.
    dy = np.diff(mf6_backwater_model["GWF_1"]["dis"]["idomain"].y)[0]
    basin_definition_ponding = create_basin_definition(
        ribasim_backwater_model.basin.node, buffersize=5.0, yoff=dy
    )
    mf6_backwater_model = add_rch_package(mf6_backwater_model)
    # mf6_backwater_model = add_well_package(mf6_backwater_model)

    msw_backwater_model.pop("sprinkling")
    msw_backwater_model.pop("mod2svat")
    msw_backwater_model["mod2svat"] = msw.CouplerMapping(
        modflow_dis=mf6_backwater_model["GWF_1"]["dis"]
    )

    mf6_backwater_model["GWF_1"].pop("sto")
    idomain = mf6_backwater_model["GWF_1"]["dis"]["idomain"]
    ss = xr.ones_like(idomain, dtype=float) * 1e-6
    ss[0, :, :] = 0.15  # phreatic layer, importent for non coupled nodes
    mf6_backwater_model["GWF_1"]["sto"] = StorageCoefficient(ss, 0.1, True, 0)

    metamod_coupling = MetaModDriverCoupling(
        mf6_model=mf6_modelname,
        mf6_recharge_package="rch_msw",
    )
    ribamod_coupling = RibaModActiveDriverCoupling(
        mf6_model=mf6_modelname,
        mf6_packages=mf6_active_river_packages + mf6_active_drainage_packages,
        ribasim_basin_definition=basin_definition,
    )
    ribameta_coupling = RibaMetaDriverCoupling(
        ribasim_basin_definition=basin_definition_ponding,
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
) -> RibaMetaMod:
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(mf6_two_basin_model)[0]
    mf6_active_river_packages = get_mf6_river_packagenames(mf6_model)
    basin_definition = create_basin_definition(
        ribasim_two_basin_model.basin.node,
        buffersize=250.0,
    )
    mf6_two_basin_model = add_rch_package(mf6_two_basin_model)
    # mf6_two_basin_model = add_well_package(mf6_two_basin_model)

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


def case_two_basin_model_users(
    mf6_two_basin_model_3layer: Modflow6Simulation,
    msw_two_basin_model_3layer: MetaSwapModel,
    ribasim_two_basin_model: ribasim.Model,
) -> RibaMetaMod:
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(mf6_two_basin_model_3layer)[0]
    mf6_active_river_packages = get_mf6_river_packagenames(mf6_model)
    basin_definition = create_basin_definition(
        ribasim_two_basin_model.basin.node,
        buffersize=250.0,
    )
    mf6_two_basin_model_3layer = add_rch_package(mf6_two_basin_model_3layer)
    mf6_two_basin_model_3layer = add_well_package(mf6_two_basin_model_3layer)

    mf6_two_basin_model_3layer["GWF_1"].pop("sto")
    idomain = mf6_two_basin_model_3layer["GWF_1"]["dis"]["idomain"]
    ss = xr.ones_like(idomain, dtype=float) * 1e-6
    ss[0, :, :] = 0.15  # phreatic layer, importent for non coupled nodes
    mf6_two_basin_model_3layer["GWF_1"]["sto"] = StorageCoefficient(ss, 0.1, True, 0)

    ribasim_two_basin_model.user_demand.add(
        ribasim.Node(7, Point(250.0, 10.0), subnetwork_id=2),
        [
            user_demand.Static(  # type: ignore
                demand=3.0,
                active=True,
                return_factor=[0.0],
                min_level=[-1.0],
                priority=[1],
            ),
        ],
    )
    ribasim_two_basin_model.user_demand.add(
        ribasim.Node(8, Point(750.0, 10.0), subnetwork_id=3),
        [
            user_demand.Static(  # type: ignore
                demand=1.5,
                active=True,
                return_factor=[0.0],
                min_level=[-1.0],
                priority=[1],
            ),
        ],
    )
    ribasim_two_basin_model.basin.node.df["subnetwork_id"].loc[
        ribasim_two_basin_model.basin.node.df["node_id"] == 2
    ] = 2
    ribasim_two_basin_model.basin.node.df["subnetwork_id"].loc[
        ribasim_two_basin_model.basin.node.df["node_id"] == 3
    ] = 3
    ribasim_two_basin_model.edge.add(
        ribasim_two_basin_model.basin[2], ribasim_two_basin_model.user_demand[7]
    )
    ribasim_two_basin_model.edge.add(
        ribasim_two_basin_model.user_demand[7], ribasim_two_basin_model.basin[2]
    )

    ribasim_two_basin_model.edge.add(
        ribasim_two_basin_model.basin[3], ribasim_two_basin_model.user_demand[8]
    )
    ribasim_two_basin_model.edge.add(
        ribasim_two_basin_model.user_demand[8], ribasim_two_basin_model.basin[3]
    )
    user_definition = create_basin_definition(
        ribasim_two_basin_model.user_demand.node, buffersize=250.0, nodes=[7]
    )
    ribasim_two_basin_model.allocation = ribasim.Allocation(
        timestep=86400.0, use_allocation=True
    )

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
        ribasim_user_demand_definition=user_definition,
    )

    return RibaMetaMod(
        ribasim_model=ribasim_two_basin_model,
        msw_model=msw_two_basin_model_3layer,
        mf6_simulation=mf6_two_basin_model_3layer,
        coupling_list=[metamod_coupling, ribamod_coupling, ribameta_coupling],
    )
