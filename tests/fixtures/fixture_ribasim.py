import numpy as np
import pandas as pd
import pytest_cases
import ribasim
import ribasim_testmodels


def add_subgrid(model: ribasim.Model) -> ribasim.Model:
    """Add 1:1 subgrid levels to model"""

    profile_df = model.basin.profile.df
    _, basin_id = np.unique(profile_df["node_id"], return_inverse=True)
    geometry = model.network.node.df.loc[profile_df["node_id"]].geometry
    subgrid_df = pd.DataFrame(
        data={
            "node_id": profile_df["node_id"],
            "subgrid_id": basin_id,
            "basin_level": profile_df["level"],
            "subgrid_level": profile_df["level"],
            "meta_x": geometry.x.to_numpy(),
            "meta_y": geometry.y.to_numpy(),
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
