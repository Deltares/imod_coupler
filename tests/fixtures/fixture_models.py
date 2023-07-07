import numpy as np
import pandas as pd
import pytest_cases
import ribasim
import ribasim_testmodels
import xarray as xr
from imod import mf6


@pytest_cases.fixture(scope="function")
def ribasim_model() -> ribasim.Model:
    return ribasim_testmodels.bucket_model()


@pytest_cases.fixture(scope="function")
def mf6_model_with_river(
    coupled_mf6_model: mf6.Modflow6Simulation,
) -> mf6.Modflow6Simulation:
    flow_model = coupled_mf6_model["GWF_1"]
    idomain = flow_model["dis"].dataset["idomain"]
    stage = xr.full_like(idomain.sel({"layer": 1}), dtype=np.floating, fill_value=3.1)
    conductance = xr.full_like(stage, 4.2)
    bottom_elevation = xr.full_like(stage, 0.3)
    bottom_elevation[{"x": 2}] = -0.1
    river_package = mf6.River(stage, conductance, bottom_elevation, save_flows=True)
    flow_model["Oosterschelde"] = river_package
    return coupled_mf6_model


@pytest_cases.fixture(scope="function")
def mf6_model_backwater_river() -> mf6.Modflow6Simulation:
    """
    This model is created to match the Ribasim backwater test model.
    """
    x = np.arange(10.0, 1020.0, 20.0)
    y = np.arange(200.0, -220.0, -20.0)
    layer = np.array([1])
    shape = (layer.size, y.size, x.size)
    dims = ["layer", "y", "x"]
    coords = {"layer": layer, "y": y, "x": x}
    idomain = xr.DataArray(data=np.ones(shape, dtype=int), coords=coords, dims=dims)

    gwf_model = mf6.GroundwaterFlowModel()
    gwf_model["dis"] = mf6.StructuredDiscretization(
        idomain=idomain, top=20.0, bottom=xr.DataArray([-10.0], dims=["layer"])
    )

    gwf_model["npf"] = mf6.NodePropertyFlow(
        icelltype=0,
        k=0.1,
        k33=0.1,
    )

    gwf_model["rch"] = mf6.Recharge(rate=xr.full_like(idomain, 0.001, dtype=float))

    stage = xr.full_like(idomain, np.nan, dtype=float)
    conductance = xr.full_like(idomain, np.nan, dtype=float)
    bottom_elevation = xr.full_like(idomain, np.nan, dtype=float)
    stage[:, 10, :] = 0.5
    # Compute conductance as wetted area (length 20.0, width 1.0, entry resistance 1.0)
    conductance[:, 10, :] = (20.0 * 1.0) / 1.0
    bottom_elevation[:, 10, :] = 0.0
    gwf_model["riv-1"] = mf6.River(
        stage=stage,
        conductance=conductance,
        bottom_elevation=bottom_elevation,
        save_flows=True,
    )
    gwf_model["drn-1"] = mf6.Drainage(
        elevation=stage,
        conductance=conductance,
    )

    gwf_model["ic"] = mf6.InitialConditions(start=0.0)
    gwf_model["sto"] = mf6.SpecificStorage(1e-3, 0.3, True, 1)
    gwf_model["oc"] = mf6.OutputControl(save_head="last", save_budget="last")

    simulation = mf6.Modflow6Simulation("backwater")
    simulation["GWF_1"] = gwf_model
    simulation["solver"] = mf6.Solution(
        modelnames=["GWF_1"],
        print_option="summary",
        csv_output=False,
        no_ptc=True,
        outer_dvclose=1.0e-4,
        outer_maximum=500,
        under_relaxation=None,
        inner_dvclose=1.0e-4,
        inner_rclose=0.001,
        inner_maximum=100,
        linear_acceleration="cg",
        scaling_method=None,
        reordering_method=None,
        relaxation_factor=0.97,
    )
    times = pd.date_range("2020-01-01", "2030-01-01", freq="M")
    simulation.create_time_discretization(additional_times=times)
    return simulation
