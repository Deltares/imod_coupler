import os
from pathlib import Path

import dotenv
import pytest


@pytest.fixture(scope="session")
def load_dotenv() -> None:
    dotenv.load_dotenv()


@pytest.fixture(scope="session")
def metaswap_lookup_table(load_dotenv) -> Path:
    return Path(os.environ["METASWAP_LOOKUP_TABLE"])


@pytest.fixture(scope="session")
def metaswap_dll(load_dotenv) -> Path:
    return Path(os.environ["METASWAP_DLL"])


@pytest.fixture(scope="session")
def metaswap_dll_dep_dir(load_dotenv) -> Path:
    return Path(os.environ["METASWAP_DLL_DEP_DIR"])


@pytest.fixture(scope="session")
def modflow_dll(load_dotenv) -> Path:
    return Path(os.environ["MODFLOW_DLL"])


@pytest.fixture(scope="session")
def imodc(load_dotenv) -> Path:
    return Path(os.environ["IMOD_COUPLER_EXECUTABLE"])
