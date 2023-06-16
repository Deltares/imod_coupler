import subprocess
from pathlib import Path
from typing import Tuple

from imod.couplers.ribamod import RibaMod
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


@parametrize_with_cases("ribamod_model", prefix="case_ribamod_")
def test_ribamod_develop(
    tmp_path_dev: Path,
    ribamod_model: RibaMod,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    imod_coupler_exec_devel: Path,
) -> None:
    """
    Test if coupled models run with the iMOD Coupler development version.
    """
    ribamod_model.write(
        tmp_path_dev,
        modflow6_dll=modflow_dll_devel,
        ribasim_dll=ribasim_dll_devel,
        ribasim_dll_dependency=ribasim_dll_dep_dir_devel,
    )

    subprocess.run(
        [imod_coupler_exec_devel, tmp_path_dev / ribamod_model._toml_name], check=True
    )
