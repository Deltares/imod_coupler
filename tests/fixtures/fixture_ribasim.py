import numpy as np
import pandas as pd
import pytest_cases
import ribasim
import ribasim_testmodels


def add_subgrid(model: ribasim.Model) -> ribasim.Model:
    """Add 1:1 subgrid levels to model"""

    profile_df = model.basin.profile.df
    _, basin_id = np.unique(profile_df["node_id"], return_inverse=True)
    geometry = model.basin.node.df["geometry"]
    x = geometry.x.iloc[basin_id].to_numpy()
    y = geometry.y.iloc[basin_id].to_numpy()
    subgrid_df = pd.DataFrame(
        data={
            "node_id": profile_df["node_id"],
            "subgrid_id": basin_id,
            "basin_level": profile_df["level"],
            "subgrid_level": profile_df["level"],
            "meta_x": x,
            "meta_y": y,
        }
    )
    model.basin.subgrid.df = subgrid_df
    return model


@pytest_cases.fixture(scope="function")
def ribasim_bucket_model() -> ribasim.Model:
    return add_subgrid(ribasim_testmodels.bucket_model())


@pytest_cases.fixture(scope="function")
def ribasim_backwater_model() -> ribasim.Model:
    return add_subgrid(ribasim_testmodels.backwater_model())


@pytest_cases.fixture(scope="function")
def ribasim_two_basin_model() -> ribasim.Model:
    return ribasim_testmodels.two_basin_model()


@pytest_cases.fixture(scope="function")
def ribasim_two_basin_model_dbg() -> ribasim.Model:
    model = ribasim_testmodels.two_basin_model()
    #   model.logging.verbosity = ribasim.Verbosity("debug")
    #   model.logging.verbosity = "debug"
    return model
