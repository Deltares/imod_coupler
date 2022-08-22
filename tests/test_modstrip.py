from pathlib import Path

import pytest


@pytest.fixture(scope="function")
def data_loc(request):
    """
    Return the directory of the test data

    Based on: https://stackoverflow.com/a/44935451

    """

    return Path(request.fspath).parent / "data"


@pytest.fixture(scope="function")
def modstrip_loc(data_loc):
    """
    Return the directory of the modstrip data
    """

    return data_loc / "modstrip"
