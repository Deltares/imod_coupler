import os
from pathlib import Path

import dotenv
import pytest


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
def dflowfm_dll_dep_dir_devel() -> Path:
    return Path(os.environ["DFLOWFM_DLL_DEP_DIR_DEVEL"])


@pytest.fixture(scope="session")
def dflowfm_dll_dep_dir_regression() -> Path:
    return Path(os.environ["DFLOWFM_DLL_DEP_DIR_REGRESSION"])


@pytest.fixture(scope="session")
def dflowfm_dll_devel() -> Path:
    return Path(os.environ["DFLOWFM_DLL_DEVEL"])


@pytest.fixture(scope="session")
def dflowfm_dll_regression() -> Path:
    return Path(os.environ["DFLOWFM_DLL_REGRESSION"])


@pytest.fixture(scope="function")
def modstrip_loc(request) -> Path:
    """
    Return the directory of the modstrip data

    Based on: https://stackoverflow.com/a/44935451

    """

    return Path(request.fspath).parent / "data" / "modstrip"


@pytest.fixture(scope="function")
def dflowfm_initial_inputfiles_folder(request) -> Path:
    """
    Return the directory of the DFLOW-FM example problem input data
    """

    return Path(request.fspath).parent / "data" / "dflowfm_example"


@pytest.fixture(scope="function")
def dflow1d_mapping_file(request) -> Path:
    """
    Return the directory of the mapping example problem input data
    """
    return (
        Path(request.fspath).parent / "data" / "mapper_input" / "DFLOWFM1D_POINTS.DAT"
    )


@pytest.fixture(scope="function")
def mapping_file_mf6_river_to_dfm_1d_q(request) -> Path:
    return Path(request.fspath).parent / "data" / "mapper_input" / "MFRIVTODFM1D_Q.DMM"


@pytest.fixture(scope="function")
def mapping_file_dfm_1d_waterlevel_to_mf6_river_stage(request) -> Path:
    return (
        Path(request.fspath).parent
        / "data"
        / "mapper_input"
        / "DFM1DWATLEVTOMFRIV_H.DMM"
    )


@pytest.fixture(scope="session")
def dflowfm_dll() -> Path:
    return Path(os.environ["DFLOWFM_DLL_DEVEL"])


@pytest.fixture(scope="function")
def tmodel_input_folder(request) -> Path:
    return Path(request.fspath).parent / "data" / "t_model"


@pytest.fixture(scope="function")
def tmodel_f_input_folder(request) -> Path:
    return Path(request.fspath).parent / "data" / "t_model_f"


@pytest.fixture(scope="function")
def reference_result_folder(request) -> Path:
    return Path(request.fspath).parent / "test_reference_output"


@pytest.fixture(scope="function")
def test_data_folder(request) -> Path:
    return Path(request.fspath).parent / "data"
