
from collections.abc import Callable
from pathlib import Path

from primod.metamod import MetaMod
from pytest_cases import parametrize_with_cases
from tests.test_imod_coupler.test_metamod import mf6_output_files


@parametrize_with_cases("metamod_regrid")
def test_metamod_regrid(
    tmp_path_dev: Path,
    metamod_regrid: MetaMod,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
    run_coupler_function: Callable[[Path], None],
) -> None:
    """
    Test if coupled models run with the iMOD Coupler development version.
    """
    metamod_regrid.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )

    run_coupler_function(tmp_path_dev / metamod_regrid._toml_name)

    # Test if MetaSWAP output written
    assert len(list((tmp_path_dev / "MetaSWAP").glob("*/*.idf"))) == 1704

    # Test if Modflow6 output written
    headfile, cbcfile, _, _ = mf6_output_files(tmp_path_dev)

    assert headfile.exists()
    assert cbcfile.exists()
    # If computation failed, Modflow6 usually writes a headfile and cbcfile of 0
    # bytes.
    assert headfile.stat().st_size > 0
    assert cbcfile.stat().st_size > 0