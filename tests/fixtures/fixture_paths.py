import os
from pathlib import Path

import dotenv
import pytest
from pytest import FixtureRequest


@pytest.fixture
def tmp_path_dev(
    tmp_path: Path,
) -> Path:
    return tmp_path / "develop"


@pytest.fixture
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


@pytest.fixture(scope="function")
def modstrip_loc(request: FixtureRequest) -> Path:
    """
    Return the directory of the modstrip data

    Based on: https://stackoverflow.com/a/44935451

    """

    return request.path.parent / "data" / "modstrip"


@pytest.fixture(scope="function")
def tki_ai_model_local(request: FixtureRequest) -> Path:
    return request.path.parent / "data" / "tki_ai_model" / "local_model"


@pytest.fixture(scope="function")
def tki_ai_model_global(request: FixtureRequest) -> Path:
    return request.path.parent / "data" / "tki_ai_model" / "global_model"


@pytest.fixture(scope="function")
def test_data_folder(request: FixtureRequest) -> Path:
    return request.path.parent / "data"


@pytest.fixture(scope="function")
def reference_result_folder(request: FixtureRequest) -> Path:
    return request.path.parent / "reference_output"
