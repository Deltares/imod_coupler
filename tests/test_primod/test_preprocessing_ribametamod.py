from pathlib import Path

import geopandas as gpd
import imod
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from imod.mf6 import Drainage, River
from imod.mf6.model import GroundwaterFlowModel
from imod.mf6.simulation import Modflow6Simulation
from numpy.testing import assert_equal
from primod.ribametamod.ribametamod import RibaMetaMod
from primod.ribametamod.ribametamod import DriverCoupling
from primod.ribametamod import (
    RibaMetaMod,
    NodeSvatMapping,
    RechargeSvatMapping,
    WellSvatMapping,
)
from shapely.geometry import Polygon

# tomllib part of Python 3.11, else use tomli
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


def create_basin_definition(coupled_mf6_model, ribasim_two_basin_model, buffersize: float) -> gpd.GeoDataFrame:
    _, mf6_model = get_mf6_gwf_modelnames(coupled_mf6_model)[0]
    _, xmin, xmax, _, ymin, ymax = imod.util.spatial_reference(
        mf6_model["dis"]["idomain"]
    )
    ribasim_model = ribasim_two_basin_model
    node = ribasim_model.network.node.df
    basin_nodes = ribasim_model.basin.static.df["node_id"].unique()
    basin_geometry = node.loc[basin_nodes].geometry
    # Call to_numpy() to get rid of the index
    basin_definition = gpd.GeoDataFrame(
        data={"node_id": basin_nodes},
        geometry=basin_geometry.buffer(buffersize).to_numpy(),
    )

    return basin_definition


def test_ribametamod_write(
    ribasim_two_basin_model, prepared_msw_model, coupled_mf6_model, tmp_path
):
    basin_definition = create_basin_definition(coupled_mf6_model, 
                                               ribasim_two_basin_model, 
                                               buffersize = 10)
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(coupled_mf6_model)[0]
    mf6_river_packages = get_mf6_river_packagenames(mf6_model)

    driver_coupling = DriverCoupling(
        mf6_model=mf6_modelname,
        mf6_active_river_packages=mf6_river_packages,
    )

    coupled_models = RibaMetaMod(
        ribasim_two_basin_model,
        prepared_msw_model,
        coupled_mf6_model,
        coupling_list=[driver_coupling],
        basin_definition=basin_definition,
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey="wells_msw",        
    )
    output_dir = tmp_path / "ribametamod"
    coupling_dict = coupled_models.write_exchanges(output_dir, "rch_msw", "wells_msw")


    exchange_path = Path("exchanges") / "riv-1.tsv"
    expected_dict = {
        "mf6_model": "GWF_1",
        "mf6_active_river_packages": {"riv-1": exchange_path.as_posix()},
        "mf6_passive_river_packages": {},
        "mf6_active_drainage_packages": {},
        "mf6_passive_drainage_packages": {},
    }
    assert coupling_dict == expected_dict

    assert (output_dir / exchange_path).exists()
    exchange_df = pd.read_csv(output_dir / exchange_path, sep="\t")
    expected_df = pd.DataFrame(data={"basin_index": [0], "bound_index": [0]})
    assert exchange_df.equals(expected_df)

    ### to be added: asserts on metaswap-ribasim specific tables 


def test_ribametamod_write_toml(
    ribasim_two_basin_model, prepared_msw_model, coupled_mf6_model, tmp_path
):
    basin_definition = create_basin_definition(coupled_mf6_model, 
                                               ribasim_two_basin_model, 
                                               buffersize = 10)
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(coupled_mf6_model)[0]
    mf6_river_packages = get_mf6_river_packagenames(mf6_model)

    driver_coupling = DriverCoupling(
        mf6_model=mf6_modelname,
        mf6_active_river_packages=mf6_river_packages,
    )

    coupled_models = RibaMetaMod(
        ribasim_two_basin_model,
        prepared_msw_model,
        coupled_mf6_model,
        coupling_list=[driver_coupling],
        basin_definition=basin_definition,
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey="wells_msw",        
    )

    output_dir = tmp_path / "ribamod"
    coupling_dict = coupled_models.write_exchanges(output_dir, "rch_msw", "wells_msw")

    coupled_models.write_toml(
        output_dir, coupling_dict, "./modflow6.dll", "./ribasim.dll", "./ribasim-bin"
    )

    with open(output_dir / "imod_coupler.toml", mode="rb") as f:
        toml_dict = tomllib.load(f)

    # This contains empty tupled, which are removed in the TOML
    dict_expected = {
        "timing": False,
        "log_level": "INFO",
        "driver_type": "ribamod",
        "driver": {
            "kernels": {
                "modflow6": {
                    "dll": "./modflow6.dll",
                    "work_dir": coupled_models._modflow6_model_dir,
                },
                "ribasim": {
                    "dll": "./ribasim.dll",
                    "dll_dep_dir": "./ribasim-bin",
                    "config_file": str(Path("ribasim") / "ribasim.toml"),
                },
            },
            "coupling": [coupling_dict],
        },
    }
    assert toml_dict == dict_expected


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
