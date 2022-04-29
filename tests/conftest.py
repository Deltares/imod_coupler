import os
from pathlib import Path

import pytest
from dotenv import load_dotenv


@pytest.fixture
def database_path() -> Path:
    load_dotenv()
    database_path = Path(os.environ["METASWAP_LOOKUP_TABLE"])
    return database_path
