import os
from pathlib import Path

import dotenv
import pytest
from pytest import FixtureRequest


@pytest.fixture(scope="function")
def tmp_path_dev(
    tmp_path: Path,
) -> Path:
    return tmp_path / "develop"


@pytest.fixture(scope="function")
def tmp_path_reg(
    tmp_path: Path,
) -> Path:
    return tmp_path / "regression"


@pytest.fixture(scope="session", autouse=True)
def load_dotenv() -> None:
    dotenv.load_dotenv()


@pytest.fixture(scope="session")
def imod_coupler_exec_devel() -> Path:
    return Path(os.environ["IMOD_COUPLER_EXEC_DEVEL"])


@pytest.fixture(scope="session")
def imod_coupler_exec_regression() -> Path:
    return Path(os.environ["IMOD_COUPLER_EXEC_REGRESSION"])


@pytest.fixture(scope="session")
def metaswap_dll_dep_dir_devel() -> Path:
    return Path(os.environ["METASWAP_DLL_DEP_DIR_DEVEL"])


@pytest.fixture(scope="session")
def metaswap_dll_dep_dir_regression() -> Path:
    return Path(os.environ["METASWAP_DLL_DEP_DIR_REGRESSION"])


@pytest.fixture(scope="session")
def metaswap_dll_devel() -> Path:
    return Path(os.environ["METASWAP_DLL_DEVEL"])


@pytest.fixture(scope="session")
def metaswap_dll_regression() -> Path:
    return Path(os.environ["METASWAP_DLL_REGRESSION"])


@pytest.fixture(scope="session")
def metaswap_lookup_table() -> Path:
    return Path(os.environ["METASWAP_LOOKUP_TABLE"])


@pytest.fixture(scope="session")
def modflow_dll_devel() -> Path:
    return Path(os.environ["MODFLOW_DLL_DEVEL"])


@pytest.fixture(scope="session")
def modflow_dll_regression() -> Path:
    return Path(os.environ["MODFLOW_DLL_REGRESSION"])


@pytest.fixture(scope="session")
def ribasim_dll_dep_dir_devel() -> Path:
    return Path(os.environ["RIBASIM_DLL_DEP_DIR_DEVEL"])


@pytest.fixture(scope="session")
def ribasim_dll_dep_dir_regression() -> Path:
    return Path(os.environ["RIBASIM_DLL_DEP_DIR_REGRESSION"])


@pytest.fixture(scope="session")
def ribasim_dll_devel() -> Path:
    return Path(os.environ["RIBASIM_DLL_DEVEL"])


@pytest.fixture(scope="session")
def ribasim_dll_regression() -> Path:
    return Path(os.environ["RIBASIM_DLL_REGRESSION"])


@pytest.fixture(scope="session", autouse=False)
def user_acceptance_dir() -> Path:
    return Path(os.environ["USER_ACCEPTANCE_DIR"])


@pytest.fixture(scope="session", autouse=False)
def user_acceptance_metaswap_dbase() -> Path:
    """Path to the user acceptance metaswap database, which is 80 GB. Requires mount to access."""
    # Resolve in advance, as otherwise python will return an OSError when trying
    # to resolve at the mount point.
    return (
        Path(os.environ["USER_ACCEPTANCE_DIR"]).resolve()
        / "LHM2018_v02vae_BOFEK2020"
    )


@pytest.fixture(scope="function")
def modstrip_loc() -> Path:
    return Path(__file__).parent.parent.absolute() / "data" / "modstrip"


@pytest.fixture(scope="function")
def test_data_folder() -> Path:
    return Path(__file__).parent.parent.absolute() / "data"


@pytest.fixture(scope="function")
def reference_result_folder() -> Path:
    return Path(__file__).parent.parent.absolute() / "reference_output"


@pytest.fixture(scope="function")
def bucket_ribametamod_loc() -> Path:
    return Path(__file__).parent.parent.absolute() / "data" / "bucket_model"


@pytest.fixture(scope="function")
def ribametamod_backwater_tot_svat_ref(request: FixtureRequest) -> Path:
    return (
        request.path.parent
        / "reference_output"
        / "test_ribametamod_backwater"
        / "tot_svat_per.csv"
    )


@pytest.fixture(scope="function")
def ribametamod_bucket_tot_svat_ref(request: FixtureRequest) -> Path:
    return (
        request.path.parent
        / "reference_output"
        / "test_ribametamod_bucket"
        / "tot_svat_per.csv"
    )


@pytest.fixture(scope="function")
def ribametamod_two_basin_tot_svat_ref(request: FixtureRequest) -> Path:
    return (
        request.path.parent
        / "reference_output"
        / "test_ribametamod_two_basin"
        / "tot_svat_per.csv"
    )
