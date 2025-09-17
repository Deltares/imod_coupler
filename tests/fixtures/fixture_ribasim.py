from datetime import datetime

import numpy as np
import pandas as pd
import pytest
import pytest_cases
import ribasim
import ribasim_testmodels

from imod_coupler.kernelwrappers.ribasim_wrapper import RibasimWrapper

solver_algorithm: str = "QNDF"


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
    bucket = ribasim_testmodels.bucket_model()
    bucket.endtime = datetime(2023, 1, 1, 0, 0)
    bucket.solver.algorithm = solver_algorithm
    return add_subgrid(bucket)


@pytest_cases.fixture(scope="function")
def ribasim_bucket_model_no_subgrid() -> ribasim.Model:
    bucket = ribasim_testmodels.bucket_model()
    bucket.endtime = datetime(2023, 1, 1, 0, 0)
    bucket.solver.algorithm = solver_algorithm
    return bucket


@pytest_cases.fixture(scope="function")
def ribasim_backwater_model() -> ribasim.Model:
    backwater = ribasim_testmodels.backwater_model()
    backwater.solver.algorithm = solver_algorithm
    backwater.solver.reltol = 1e-08
    backwater.solver.abstol = 1e-08
    return add_subgrid(backwater)


@pytest_cases.fixture(scope="function")
def ribasim_two_basin_model() -> ribasim.Model:
    twobasin = ribasim_testmodels.two_basin_model()
    twobasin.solver.algorithm = solver_algorithm
    return twobasin


@pytest_cases.fixture(scope="function")
def ribasim_two_basin_model_dbg() -> ribasim.Model:
    model = ribasim_testmodels.two_basin_model()
    #   model.logging.verbosity = ribasim.Verbosity("debug")
    #   model.logging.verbosity = "debug"
    #model.solver.algorithm = solver_algorithm
    return model


@pytest.fixture(scope="session")
def ribasim_basic_model() -> ribasim.Model:
    return ribasim_testmodels.basic_model()


@pytest.fixture(scope="session")
def ribasim_basic_transient_model(ribasim_basic_model) -> ribasim.Model:
    return ribasim_testmodels.basic_transient_model(ribasim_basic_model)


@pytest.fixture(scope="session")
def ribasim_leaky_bucket_model() -> ribasim.Model:
    return ribasim_testmodels.leaky_bucket_model()


@pytest.fixture(scope="session")
def ribasim_user_demand_model() -> ribasim.Model:
    return ribasim_testmodels.user_demand_model()


@pytest.fixture(scope="session", autouse=True)
def load_julia(
    ribasim_dll_devel,
    ribasim_dll_dep_dir_devel,
) -> None:
    libribasim = RibasimWrapper(ribasim_dll_devel, ribasim_dll_dep_dir_devel)
    libribasim.init_julia()


@pytest.fixture(scope="function")
def libribasim(ribasim_dll_devel, ribasim_dll_dep_dir_devel, request) -> RibasimWrapper:
    # lib_path, lib_folder = libribasim_paths
    libribasim = RibasimWrapper(ribasim_dll_devel, ribasim_dll_dep_dir_devel)

    # If initialized, call finalize() at end of use
    request.addfinalizer(libribasim.__del__)
    return libribasim
