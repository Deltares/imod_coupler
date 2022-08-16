import os
from pathlib import Path

import dotenv
import pytest

# This imports fixtures from iMOD Python
pytest_plugins = ["imod_msw_mf6"]


@pytest.fixture(scope="session")
def load_dotenv() -> None:
    dotenv.load_dotenv()


@pytest.fixture(scope="session")
def imod_coupler_exec_devel(load_dotenv) -> Path:
    return Path(os.environ["IMOD_COUPLER_EXEC_DEVEL"])


@pytest.fixture(scope="session")
def imod_coupler_exec_regression(load_dotenv) -> Path:
    return Path(os.environ["IMOD_COUPLER_EXEC_REGRESSION"])


@pytest.fixture(scope="session")
def metaswap_dll_dep_dir_devel(load_dotenv) -> Path:
    return Path(os.environ["METASWAP_DLL_DEP_DIR_DEVEL"])


@pytest.fixture(scope="session")
def metaswap_dll_dep_dir_regression(load_dotenv) -> Path:
    return Path(os.environ["METASWAP_DLL_DEP_DIR_REGRESSION"])


@pytest.fixture(scope="session")
def metaswap_dll_devel(load_dotenv) -> Path:
    return Path(os.environ["METASWAP_DLL_DEVEL"])


@pytest.fixture(scope="session")
def metaswap_dll_regression(load_dotenv) -> Path:
    return Path(os.environ["METASWAP_DLL_REGRESSION"])


@pytest.fixture(scope="session")
def metaswap_lookup_table(load_dotenv) -> Path:
    return Path(os.environ["METASWAP_LOOKUP_TABLE"])


@pytest.fixture(scope="session")
def modflow_dll_devel(load_dotenv) -> Path:
    return Path(os.environ["MODFLOW_DLL_DEVEL"])


@pytest.fixture(scope="session")
def modflow_dll_regression(load_dotenv) -> Path:
    return Path(os.environ["MODFLOW_DLL_REGRESSION"])
