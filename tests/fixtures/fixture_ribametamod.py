from pathlib import Path

import numpy as np
import pytest_cases
import xarray as xr
from imod import idf, mf6, msw

from .common import create_wells_max_layer
from .fixture_metaswap import metaswap_model


def make_msw_model(
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

    # no svats where river is defined
    no_river = xr.full_like(area, fill_value=True, dtype=np.bool_)
    for sys in gwf["GWF_1"].keys():
        package = gwf["GWF_1"][sys]
        if isinstance(package, mf6.River):
            cond = package["conductance"]
            if "layer" in cond.dims:
                cond = cond.isel(layer=0, drop=True)
            no_river.values = np.logical_and(
                cond.isna().to_numpy(), no_river.notnull().to_numpy()
            )
    area = (area.assign_coords(subunit=0).expand_dims(subunit=isubunits)) / nsubunits
    area = area.where((area.subunit < nsubunits) & no_river)

    active = (xr.ones_like(idomain_flat) == 1).where(
        nsubunits.notnull() & no_river, other=False
    )

    # Clip off
    modflow_active = idomain.sel(layer=1, drop=True).astype(bool)

    area = area.where(modflow_active)
    active = active & modflow_active

    # Well
    ncol = idomain.x.size
    nrow = idomain.y.size
    well = create_wells_max_layer(nrow, ncol, idomain)

    dis = gwf["GWF_1"]["dis"]

    return metaswap_model(times, area, active, well, dis, unsaturated_database)


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
    msw_model = make_msw_model(mf6_model, nsubunits)
    # Override unsat_svat_path with path from environment
    msw_model.simulation_settings["unsa_svat_path"] = (
        msw_model._render_unsaturated_database_path(metaswap_lookup_table)
    )
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
    mf6_two_basin_model_3layer: mf6.GroundwaterFlowModel,
    metaswap_lookup_table: Path,
) -> msw.MetaSwapModel:
    return ad_msw_model(mf6_two_basin_model_3layer, metaswap_lookup_table)
