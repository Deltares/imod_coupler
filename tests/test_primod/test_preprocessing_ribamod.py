from pathlib import Path

import geopandas as gpd
import imod
import numpy as np
import pandas as pd
import pytest
import ribasim
from imod.mf6 import Drainage, GroundwaterFlowModel, River
from imod.mf6.simulation import Modflow6Simulation
from primod import RibaModActiveDriverCoupling, RibaModPassiveDriverCoupling
from primod.driver_coupling.util import (
    _nullify_ribasim_exchange_input,
    _validate_keys,
    _validate_time_window,
)
from primod.ribamod import RibaMod
from shapely.geometry import Polygon

# tomllib part of Python 3.11, else use tomli
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


@pytest.fixture
def basin_definition(mf6_bucket_model, ribasim_bucket_model) -> gpd.GeoDataFrame:
    _, mf6_model = get_mf6_gwf_modelnames(mf6_bucket_model)[0]
    _, xmin, xmax, _, ymin, ymax = imod.util.spatial_reference(
        mf6_model["dis"]["idomain"]
    )
    node_id = ribasim_bucket_model.basin.static.df["node_id"].unique()
    polygon = Polygon(
        [
            [xmin, ymin],
            [xmax, ymin],
            [xmax, ymax],
            [xmin, ymax],
        ]
    )
    return gpd.GeoDataFrame(data={"node_id": node_id}, geometry=[polygon])


def test_validate_time_window(mf6_bucket_model, ribasim_bucket_model):
    times = pd.date_range("1970-01-01", "1971-01-01", freq="D")
    # override time discretization
    mf6_bucket_model.create_time_discretization(additional_times=times)
    with pytest.raises(
        ValueError, match="Ribasim simulation time window does not match MODFLOW6"
    ):
        _validate_time_window(ribasim_bucket_model, mf6_bucket_model)


def test_validate_keys(mf6_bucket_model):
    with pytest.raises(ValueError, match="active and passive keys share members"):
        _validate_keys(
            mf6_bucket_model,
            active_keys=["riv-1"],
            passive_keys=["riv-1"],
            expected_type=River,
        )

    with pytest.raises(ValueError, match="keys with expected type"):
        _validate_keys(
            mf6_bucket_model,
            active_keys=["riv-1"],
            passive_keys=[],
            expected_type=Drainage,
        )


def test_ribamod_write__error(
    ribasim_bucket_model, mf6_bucket_model, basin_definition, tmp_path
):
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(mf6_bucket_model)[0]
    mf6_river_packages = get_mf6_river_packagenames(mf6_model)

    driver_coupling = RibaModActiveDriverCoupling(
        mf6_model=mf6_modelname,
        ribasim_basin_definition=basin_definition,
        mf6_packages=mf6_river_packages,
    )

    # Remove subgrid
    ribasim_bucket_model.basin.subgrid.df = None

    coupled_models = RibaMod(
        ribasim_bucket_model,
        mf6_bucket_model,
        coupling_list=[driver_coupling],
    )
    output_dir = tmp_path / "ribamod"

    with pytest.raises(
        ValueError,
        match="ribasim.model.basin.subgrid must be defined for actively coupled packages.",
    ):
        coupled_models.write_exchanges(output_dir)


def test_ribamod_write(
    ribasim_bucket_model, mf6_bucket_model, basin_definition, tmp_path
):
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(mf6_bucket_model)[0]
    mf6_river_packages = get_mf6_river_packagenames(mf6_model)

    driver_coupling = RibaModActiveDriverCoupling(
        mf6_model=mf6_modelname,
        ribasim_basin_definition=basin_definition,
        mf6_packages=mf6_river_packages,
    )

    coupled_models = RibaMod(
        ribasim_bucket_model,
        mf6_bucket_model,
        coupling_list=[driver_coupling],
    )
    output_dir = tmp_path / "ribamod"
    coupling_dict = coupled_models.write_exchanges(output_dir)

    expected_dict = {
        "mf6_model": "GWF_1",
        "mf6_active_river_packages": {"riv-1": "./exchanges/riv-1.tsv"},
        "mf6_passive_river_packages": {},
        "mf6_active_drainage_packages": {},
        "mf6_passive_drainage_packages": {},
    }
    assert coupling_dict == expected_dict

    exchange_path = Path("./exchanges/riv-1.tsv")
    assert (output_dir / exchange_path).exists()
    exchange_df = pd.read_csv(output_dir / exchange_path, sep="\t")
    expected_df = pd.DataFrame(
        data={"basin_index": [0], "bound_index": [0], "subgrid_index": [0]}
    )
    assert exchange_df.equals(expected_df)


def test_ribamod_write_toml(
    ribasim_bucket_model, mf6_bucket_model, basin_definition, tmp_path
):
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(mf6_bucket_model)[0]
    mf6_river_packages = get_mf6_river_packagenames(mf6_model)

    driver_coupling = RibaModPassiveDriverCoupling(
        mf6_model=mf6_modelname,
        ribasim_basin_definition=basin_definition,
        mf6_packages=mf6_river_packages,
    )

    coupled_models = RibaMod(
        ribasim_bucket_model,
        mf6_bucket_model,
        coupling_list=[driver_coupling],
    )

    output_dir = tmp_path / "ribamod"
    # Exception expected due to river package in a passive ribamod driver coupling
    with pytest.raises(TypeError) as e_info:
        coupling_dict = coupled_models.write_exchanges(output_dir)
    assert "Expected Drainage packages for passive coupling, received: River" in str(
        e_info.value
    )

    # Remove riv-1 (river) and api_riv-1 packages, add drn-1 (drainage) package
    conductance = mf6_bucket_model["GWF_1"]["riv-1"]["conductance"]
    bottom_elevation = mf6_bucket_model["GWF_1"]["riv-1"]["bottom_elevation"]
    mf6_bucket_model["GWF_1"].pop("riv-1")
    mf6_bucket_model["GWF_1"].pop("api_riv-1")
    mf6_bucket_model["GWF_1"]["drn-1"] = Drainage(
        elevation=bottom_elevation, conductance=conductance
    )
    driver_coupling.mf6_packages.remove("riv-1")
    driver_coupling.mf6_packages.append("drn-1")

    coupling_dict = coupled_models.write_exchanges(output_dir)

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


def test_nullify_ribasim_exchange_input(
    ribasim_bucket_model, mf6_bucket_model, basin_definition
):
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(mf6_bucket_model)[0]
    mf6_river_packages = get_mf6_river_packagenames(mf6_model)

    driver_coupling = RibaModPassiveDriverCoupling(
        mf6_model=mf6_modelname,
        ribasim_basin_definition=basin_definition,
        mf6_packages=mf6_river_packages,
    )

    coupled_models = RibaMod(
        ribasim_bucket_model,
        mf6_bucket_model,
        coupling_list=[driver_coupling],
    )

    # Should be not-NA before method call.
    df = coupled_models.ribasim_model.basin.static.df
    df.loc[:, ["drainage", "infiltration"]] = 0.0
    assert df.loc[:, ["drainage", "infiltration"]].notna().all(axis=None)

    coupled_basin_node_ids = np.array([1])
    _nullify_ribasim_exchange_input(
        ribasim_component=coupled_models.ribasim_model.basin,
        coupled_node_ids=coupled_basin_node_ids,
        columns=["drainage", "infiltration"],
    )
    # Should now be NA after call.
    df = coupled_models.ribasim_model.basin.static.df
    assert df.loc[:, ["drainage", "infiltration"]].isna().all(axis=None)


def test_nullify_on_write(
    tmp_path: Path,
    ribasim_two_basin_model: ribasim.Model,
    mf6_partial_two_basin_model: imod.mf6.Modflow6Simulation,
) -> None:
    mf6_modelname, mf6_model = get_mf6_gwf_modelnames(mf6_partial_two_basin_model)[0]
    mf6_river_packages = get_mf6_river_packagenames(mf6_model)

    # This basin definition is still a point geometry.
    # This mean it will be rasterized to just two pixels.
    gdf = ribasim_two_basin_model.basin.node.df
    driver_coupling = RibaModPassiveDriverCoupling(
        mf6_model=mf6_modelname,
        ribasim_basin_definition=gdf,
        mf6_packages=mf6_river_packages,
    )

    coupled_models = RibaMod(
        ribasim_two_basin_model,
        mf6_partial_two_basin_model,
        coupling_list=[driver_coupling],
    )

    coupled_models.write_exchanges(tmp_path)

    coupled_models.write(
        directory=tmp_path,
        modflow6_dll="a",
        ribasim_dll="b",
        ribasim_dll_dependency="c",
    )
    # check if columns will be nullified correctly
    node_id = coupled_models.ribasim_model.basin.node.df["node_id"].to_numpy()
    df = pd.DataFrame.from_dict(
        {
            "node_id": node_id,
            "drainage": np.ones_like(node_id),
            "infiltration": np.ones_like(node_id),
        }
    )
    coupled_models.ribasim_model.basin.static.df = df
    coupled_models.write(
        directory=tmp_path,
        modflow6_dll="a",
        ribasim_dll="b",
        ribasim_dll_dependency="c",
    )
    df = coupled_models.ribasim_model.basin.static.df
    # Basin 2 is coupled, so drainage & infiltration should be NaN.
    assert (
        df.loc[df["node_id"] == 2, ["drainage", "infiltration"]].isna().all(axis=None)
    )
    # Basin 3 is uncoupled, terms should be preserved.
    assert (
        df.loc[df["node_id"] == 3, ["drainage", "infiltration"]].notna().all(axis=None)
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
