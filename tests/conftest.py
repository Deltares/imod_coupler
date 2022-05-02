import os
from pathlib import Path

import pytest
from dotenv import load_dotenv


@pytest.fixture(scope="session")
def database_path() -> Path:
    load_dotenv()
    database_path = Path(os.environ["METASWAP_LOOKUP_TABLE"])
    return database_path


@pytest.fixture(scope="session")
def imodc_path() -> Path:
    load_dotenv()
    imodc_path = Path(os.environ["IMOD_COUPLER_EXECUTABLE"])
    return imodc_path
