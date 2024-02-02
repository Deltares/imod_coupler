from pathlib import Path

import numpy as np
import pytest_cases
import xarray as xr
from imod import mf6, msw

from .common import create_wells_max_layer


def create_msw_model(
    gwf: mf6.GroundwaterFlowModel, nsubunits: xr.DataArray(np.int32) | None = None
) -> msw.MetaSwapModel:
    times = gwf["time_discretization"]["time"]
    unsaturated_database = "./unsat_database"

    idomain = gwf["GWF_1"]["dis"]["idomain"]
    if "layer" in idomain.dims:
        idomain_flat = idomain.sel(layer=1)
    if nsubunits is None:
        nsubunits = xr.ones_like(idomain)

    isubunits = np.arange(nsubunits.max())
    area = xr.ones_like(idomain_flat, dtype=np.float64) * (
        np.diff(idomain.x)[0] * -np.diff(idomain.y)[0]
    )
    area = (area.assign_coords(subunit=0).expand_dims(subunit=isubunits)) / nsubunits
    area = area.where(area.subunit < nsubunits)

    active = (xr.ones_like(idomain_flat) == 1).where(nsubunits.notnull(), other=False)

    # Clip off
    modflow_active = idomain.sel(layer=1, drop=True).astype(bool)

    area = area.where(modflow_active)
    active = active & modflow_active

    # fmt: on
    msw_grid = xr.ones_like(active, dtype=float)

    precipitation = msw_grid.expand_dims(time=times[:-1]).drop_vars("layer")
    evapotranspiration = msw_grid.expand_dims(time=times[:-1]).drop_vars("layer") * 10.0

    # Vegetation
    day_of_year = np.arange(1, 367)
    vegetation_index = np.arange(1, 4)

    coords = {"day_of_year": day_of_year, "vegetation_index": vegetation_index}

    soil_cover = xr.DataArray(
        data=np.ones(day_of_year.shape + vegetation_index.shape),
        coords=coords,
        dims=("day_of_year", "vegetation_index"),
    )
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

    # Well
    ncol = idomain.x.size
    nrow = idomain.y.size
    well = create_wells_max_layer(nrow, ncol, idomain)

    # Modflow 6
    dis = gwf["GWF_1"]["dis"]

    # Initiate model
    msw_model = msw.MetaSwapModel(unsaturated_database=unsaturated_database)
    msw_model["grid"] = msw.GridData(
        area,
        xr.full_like(area, 1, dtype=int),
        xr.full_like(area, 1.0, dtype=float),
        xr.full_like(active, 1.0, dtype=float),
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


def ad_msw_model(
    mf6_model: mf6.GroundwaterFlowModel,
    metaswap_lookup_table: Path,
) -> msw.MetaSwapModel:
    # for now only 1-1 svat-mf6node coupling
    nsubunits = xr.ones_like(
        mf6_model["GWF_1"]["dis"]["idomain"].sel(layer=1, drop=True),
        dtype=np.int32,
    )
    # No svats in nodes with river definitions
    # TODO check how to deal with area-wide drn-packages for olf,
    # packages that represent tube-draiange and olf should be skipped here.
    for package in mf6_model["GWF_1"]:
        if isinstance(package, mf6.River):
            stage = mf6_model["GWF_1"][package]["stage"]
            if "layer" in stage.dims:
                stage = stage.sel(layer=1, drop=True)
            nsubunits = nsubunits.where(stage.isna())
        elif isinstance(package, mf6.Drainage):
            elevation = mf6_model["GWF_1"][package]["elevation"]
            if "layer" in elevation.dims:
                elevation = elevation.sel(layer=1, drop=True)
            nsubunits = nsubunits.where(elevation.isna())
    msw_model = create_msw_model(mf6_model, nsubunits)
    # Override unsat_svat_path with path from environment
    msw_model.simulation_settings[
        "unsa_svat_path"
    ] = msw_model._render_unsaturated_database_path(metaswap_lookup_table)
    return msw_model


@pytest_cases.fixture(scope="function")
def msw_bucket_model(
    mf6_bucket_model: mf6.GroundwaterFlowModel,
    metaswap_lookup_table: Path,
) -> msw.MetaSwapModel:
    return ad_msw_model(mf6_bucket_model, metaswap_lookup_table)


@pytest_cases.fixture(scope="function")
def msw_backwater_model(
    mf6_backwater_model: mf6.GroundwaterFlowModel,
    metaswap_lookup_table: Path,
) -> msw.MetaSwapModel:
    return ad_msw_model(mf6_backwater_model, metaswap_lookup_table)


@pytest_cases.fixture(scope="function")
def msw_two_basin_model(
    mf6_two_basin_model: mf6.GroundwaterFlowModel,
    metaswap_lookup_table: Path,
) -> msw.MetaSwapModel:
    return ad_msw_model(mf6_two_basin_model, metaswap_lookup_table)
