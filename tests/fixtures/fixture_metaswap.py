from pathlib import Path

import numpy as np
import pandas as pd
import pytest_cases
import xarray as xr
from imod import mf6, msw
from numpy import nan

from .common import create_wells, get_times, grid_sizes


def metaswap_model(
    times: list[pd.date_range],
    area: xr.DataArray,
    active: xr.DataArray,
    well: mf6.WellDisStructured,
    dis: mf6.StructuredDiscretization,
    unsaturated_database: str,
) -> msw.MetaSwapModel:
    # fmt: on
    msw_grid = xr.ones_like(active, dtype=float)

    precipitation = msw_grid.expand_dims(time=times[:-1])
    evapotranspiration = msw_grid.expand_dims(time=times[:-1]) * 10.0
    if "layer" in msw_grid.coords:
        precipitation = precipitation.drop_vars("layer")
        evapotranspiration = evapotranspiration.drop_vars("layer")

    # Vegetation
    day_of_year = np.arange(1, 367)
    vegetation_index = np.arange(1, 4)

    coords = {"day_of_year": day_of_year, "vegetation_index": vegetation_index}

    soil_cover = xr.DataArray(
        data=np.zeros(day_of_year.shape + vegetation_index.shape),
        coords=coords,
        dims=("day_of_year", "vegetation_index"),
    )
    soil_cover[132:254, :] = 1.0
    leaf_area_index = soil_cover * 3

    vegetation_factor = xr.zeros_like(soil_cover)
    vegetation_factor[132:142, :] = 0.7
    vegetation_factor[142:152, :] = 0.9
    vegetation_factor[152:162, :] = 1.0
    vegetation_factor[162:192, :] = 1.2
    vegetation_factor[192:244, :] = 1.1
    vegetation_factor[244:254, :] = 0.7

    # Landuse
    landuse_index = np.arange(1, 4)
    names = ["grassland", "maize", "potatoes"]

    coords = {"landuse_index": landuse_index}

    landuse_names = xr.DataArray(data=names, coords=coords, dims=("landuse_index",))
    vegetation_index_da = xr.DataArray(
        data=vegetation_index, coords=coords, dims=("landuse_index",)
    )
    lu = xr.ones_like(vegetation_index_da, dtype=float)

    # Initiate model
    msw_model = msw.MetaSwapModel(unsaturated_database=unsaturated_database)
    msw_model["grid"] = msw.GridData(
        area,
        xr.full_like(area, 1, dtype=int),
        xr.full_like(area, 1.0, dtype=float),
        xr.full_like(active, dis["top"], dtype=float),  # surfrace level
        xr.full_like(active, 1, dtype=int),
        active,
    )

    msw_model["ic"] = msw.InitialConditionsRootzonePressureHead(initial_pF=2.2)

    # Meteo
    msw_model["meteo_grid"] = msw.MeteoGrid(precipitation, evapotranspiration)
    msw_model["mapping_prec"] = msw.PrecipitationMapping(precipitation)
    msw_model["mapping_evt"] = msw.EvapotranspirationMapping(precipitation * 1.5)

    # Sprinkling
    msw_model["sprinkling"] = msw.Sprinkling(
        max_abstraction_groundwater=xr.full_like(msw_grid, 100.0),
        max_abstraction_surfacewater=xr.full_like(msw_grid, 100.0),
        well=well,
    )

    # Ponding
    msw_model["ponding"] = msw.Ponding(
        ponding_depth=xr.full_like(area, 0.0),
        runon_resistance=xr.full_like(area, 1.0),
        runoff_resistance=xr.full_like(area, 1.0),
    )

    # Scaling Factors
    msw_model["scaling"] = msw.ScalingFactors(
        scale_soil_moisture=xr.full_like(area, 1.0),
        scale_hydraulic_conductivity=xr.full_like(area, 1.0),
        scale_pressure_head=xr.full_like(area, 1.0),
        depth_perched_water_table=xr.full_like(msw_grid, 1.0),
    )

    # Infiltration
    msw_model["infiltration"] = msw.Infiltration(
        infiltration_capacity=xr.full_like(area, 1.0),
        downward_resistance=xr.full_like(msw_grid, -9999.0),
        upward_resistance=xr.full_like(msw_grid, -9999.0),
        bottom_resistance=xr.full_like(msw_grid, -9999.0),
        extra_storage_coefficient=xr.full_like(msw_grid, 0.1),
    )

    # Vegetation
    msw_model["crop_factors"] = msw.AnnualCropFactors(
        soil_cover=soil_cover,
        leaf_area_index=leaf_area_index,
        interception_capacity=xr.zeros_like(soil_cover),
        vegetation_factor=vegetation_factor,
        interception_factor=xr.ones_like(soil_cover),
        bare_soil_factor=xr.ones_like(soil_cover),
        ponding_factor=xr.ones_like(soil_cover),
    )

    # Landuse options
    msw_model["landuse_options"] = msw.LanduseOptions(
        landuse_name=landuse_names,
        vegetation_index=vegetation_index_da,
        jarvis_o2_stress=xr.ones_like(lu),
        jarvis_drought_stress=xr.ones_like(lu),
        feddes_p1=xr.full_like(lu, 99.0),
        feddes_p2=xr.full_like(lu, 99.0),
        feddes_p3h=lu * [-2.0, -4.0, -3.0],
        feddes_p3l=lu * [-8.0, -5.0, -5.0],
        feddes_p4=lu * [-80.0, -100.0, -100.0],
        feddes_t3h=xr.full_like(lu, 5.0),
        feddes_t3l=xr.full_like(lu, 1.0),
        threshold_sprinkling=lu * [-8.0, -5.0, -5.0],
        fraction_evaporated_sprinkling=xr.full_like(lu, 0.05),
        gift=xr.full_like(lu, 20.0),
        gift_duration=xr.full_like(lu, 0.25),
        rotational_period=lu * [10, 7, 7],
        start_sprinkling_season=lu * [120, 180, 150],
        end_sprinkling_season=lu * [230, 230, 240],
        interception_option=xr.ones_like(lu, dtype=int),
        interception_capacity_per_LAI=xr.zeros_like(lu),
        interception_intercept=xr.ones_like(lu),
    )

    # Metaswap Mappings
    msw_model["mod2svat"] = msw.CouplerMapping(modflow_dis=dis, well=well)

    # Output Control
    msw_model["oc_idf"] = msw.IdfMapping(area, -9999.0)
    msw_model["oc_var"] = msw.VariableOutputControl()
    msw_model["oc_time"] = msw.TimeOutputControl(time=times)

    return msw_model


def make_msw_model(idomain: xr.DataArray) -> msw.MetaSwapModel:
    times = get_times()
    unsaturated_database = "./unsat_database"

    x, y, layer, dx, dy, dz = grid_sizes()
    subunit = [0, 1]

    nrow = len(y)
    ncol = len(x)

    top = 0.0
    bottom = top - xr.DataArray(np.cumsum(dz), coords={"layer": layer}, dims="layer")

    # fmt: off
    relative_area = xr.DataArray(
        np.array(
            [
                [[0.5, 0.5, 0.5, 0.5, 0.5],
                 [nan, nan, nan, nan, nan],
                 [1.0, 1.0, 1.0, 1.0, 1.0]],

                [[0.5, 0.5, 0.5, 0.5, 0.5],
                 [1.0, 1.0, 1.0, 1.0, 1.0],
                 [nan, nan, nan, nan, nan]],
            ]
        ),
        dims=("subunit", "y", "x"),
        coords={"subunit": subunit, "y": y, "x": x, "dx": dx, "dy": dy}
    )

    area = relative_area * dx * -dy

    active = xr.DataArray(
        np.array(
            [[False, True, True, True, True],
             [False, True, True, True, True],
             [False, True, True, True, True]]),
        dims=("y", "x"),
        coords={"y": y, "x": x}
    )

    # Clip off 
    modflow_active = idomain.sel(layer=1, drop=True).astype(bool)

    area = area.where(modflow_active)
    active = active & modflow_active

    # Well
    well = create_wells(nrow, ncol, idomain)

    dis = mf6.StructuredDiscretization(idomain=idomain, top=top, bottom=bottom)

    return metaswap_model(times,area,active, well, dis,unsaturated_database)


@pytest_cases.fixture(scope="function")
def prepared_msw_model(
    active_idomain: xr.DataArray,
    metaswap_lookup_table: Path,
) -> msw.MetaSwapModel:
    msw_model = make_msw_model(active_idomain)
    # Override unsat_svat_path with path from environment
    msw_model.simulation_settings["unsa_svat_path"] = (
        msw_model._render_unsaturated_database_path(metaswap_lookup_table)
    )

    return msw_model


@pytest_cases.fixture(scope="function")
def prepared_msw_model_inactive(
    inactive_idomain: xr.DataArray,
    metaswap_lookup_table: Path,
) -> msw.MetaSwapModel:
    msw_model = make_msw_model(inactive_idomain)
    # Override unsat_svat_path with path from environment
    msw_model.simulation_settings["unsa_svat_path"] = (
        msw_model._render_unsaturated_database_path(metaswap_lookup_table)
    )

    return msw_model
