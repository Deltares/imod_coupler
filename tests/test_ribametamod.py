import subprocess
from pathlib import Path
from typing import Tuple

from imod.couplers.metamod import MetaMod
from pytest_cases import parametrize_with_cases


def mf6_output_files(path: Path) -> Tuple[Path, Path, Path, Path]:
    """return paths to Modflow 6 output files"""
    path_mf6 = path / "Modflow6" / "GWF_1"

    return (
        path_mf6 / "GWF_1.hds",
        path_mf6 / "GWF_1.cbc",
        path_mf6 / "dis.dis.grb",
        path_mf6 / "GWF_1.lst",
    )


def msw_output_files(path: Path) -> Path:
    path_msw = path / "MetaSWAP"
    return path_msw / "msw" / "csv" / "tot_svat_per.csv"


@parametrize_with_cases("metamod_model", prefix="case_")
def test_ribametamod_develop(
    tmp_path_dev: Path,
    metamod_model: MetaMod,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    imod_coupler_exec_devel: Path,
) -> None:
    """
    Test if coupled models run with the iMOD Coupler development version.
    """
    metamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
        ribasim_dll=ribasim_dll_devel,
        ribasim_dll_dependency=ribasim_dll_dep_dir_devel,
    )

    subprocess.run(
        [imod_coupler_exec_devel, tmp_path_dev / metamod_model._toml_name], check=True
    )

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
