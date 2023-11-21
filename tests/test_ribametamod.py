import shutil
from pathlib import Path

import tomli_w

from imod_coupler.__main__ import run_coupler


def test_metamod(
    tmp_path_dev: Path,
    modflow_dll_devel: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    metaswap_lookup_table: Path,
    bucket_ribametamod_loc: Path,
) -> None:
    """
    Test if coupled ribametamod models run with the iMOD Coupler development version.
    """
    path_dev = tmp_path_dev / "bucket_model_driver_metamod"

    shutil.copytree(bucket_ribametamod_loc, path_dev)

    toml_path = path_dev / "imod_coupler.toml"
    modflow6_dll = modflow_dll_devel
    modflow6_model_dir = path_dev / "modflow6"
    metaswap_dll = metaswap_dll_devel
    metaswap_dll_dependency = metaswap_dll_dep_dir_devel
    metaswap_model_dir = path_dev / "metaswap"

    fill_para_sim_template(path_dev / "metaswap", metaswap_lookup_table)

    write_metamod_toml(
        path_dev,
        modflow6_dll,
        modflow6_model_dir,
        metaswap_dll,
        metaswap_dll_dependency,
        metaswap_model_dir,
    )
    run_coupler(toml_path)


def test_ribamod(
    tmp_path_dev: Path,
    modflow_dll_devel: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    bucket_ribametamod_loc: Path,
) -> None:
    """
    Test if coupled ribametamod models run with the iMOD Coupler development version.
    """
    path_dev = tmp_path_dev / "bucket_model_driver_ribamod"

    shutil.copytree(bucket_ribametamod_loc, path_dev)

    toml_path = path_dev / "imod_coupler.toml"
    modflow6_dll = modflow_dll_devel
    modflow6_model_dir = path_dev / "modflow6"

    write_ribamod_toml(
        path_dev,
        modflow6_dll,
        modflow6_model_dir,
        ribasim_dll_devel,
        ribasim_dll_dep_dir_devel,
        path_dev / "ribasim" / "ribasim.toml",
    )
    run_coupler(toml_path)


def test_ribametamod(
    tmp_path_dev: Path,
    modflow_dll_devel: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    metaswap_lookup_table: Path,
    ribasim_dll_devel: Path,
    ribasim_dll_dep_dir_devel: Path,
    bucket_ribametamod_loc: Path,
) -> None:
    """
    Test if coupled ribametamod models run with the iMOD Coupler development version.
    """
    path_dev = tmp_path_dev / "bucket_model_driver_ribametamod"

    shutil.copytree(bucket_ribametamod_loc, path_dev)

    fill_para_sim_template(path_dev / "metaswap", metaswap_lookup_table)

    # toml_path = path_dev / "imod_coupler.toml"
    modflow6_dll = modflow_dll_devel
    modflow6_model_dir = path_dev / "modflow6"
    metaswap_dll = metaswap_dll_devel
    metaswap_dll_dependency = metaswap_dll_dep_dir_devel
    metaswap_model_dir = path_dev / "metaswap"

    write_ribametamod_toml(
        path_dev,
        modflow6_dll,
        modflow6_model_dir,
        metaswap_dll,
        metaswap_dll_dependency,
        metaswap_model_dir,
        ribasim_dll_devel,
        ribasim_dll_dep_dir_devel,
        path_dev / "ribasim" / "ribasim.toml",
    )
    # run_coupler(toml_path) # don't run until optional branch is merged


def write_metamod_toml(
    tmp_path_dev: str | Path,
    modflow6_dll: str | Path,
    modflow6_model_dir: str | Path,
    metaswap_dll: str | Path,
    metaswap_dll_dependency: str | Path,
    metaswap_model_dir: str | Path,
) -> None:
    """
    Write .toml file which configures the imod coupler run.
    Parameters
    ----------
    directory: str or Path
        Directory in which to write the .toml file.
    modflow6_dll: str or Path
        Path to modflow6 .dll. You can obtain this library by downloading
        `the last iMOD5 release
        <https://oss.deltares.nl/web/imod/download-imod5>`_
    metaswap_dll: str or Path
        Path to metaswap .dll. You can obtain this library by downloading
        `the last iMOD5 release
        <https://oss.deltares.nl/web/imod/download-imod5>`_
    metaswap_dll_dependency: str or Path
        Directory with metaswap .dll dependencies. Directory should contain:
        [fmpich2.dll, mpich2mpi.dll, mpich2nemesis.dll, TRANSOL.dll]. You
        can obtain these by downloading `the last iMOD5 release
        <https://oss.deltares.nl/web/imod/download-imod5>`_
    coupling_dict: dict
        Dictionary with names of coupler packages and paths to mappings.
    """
    coupler_toml = {
        "timing": False,
        "log_level": "INFO",
        "driver_type": "metamod",
        "driver": {
            "kernels": {
                "modflow6": {
                    "dll": str(modflow6_dll),
                    "work_dir": str(modflow6_model_dir),
                },
                "metaswap": {
                    "dll": str(metaswap_dll),
                    "work_dir": str(metaswap_model_dir),
                    "dll_dep_dir": str(metaswap_dll_dependency),
                },
            },
            "coupling": [
                {
                    "enable_sprinkling": False,
                    "mf6_model": "GWF_1",
                    "mf6_msw_recharge_pkg": "rch_msw",
                    "mf6_msw_node_map": "exchanges/nodenr2svat.dxc",
                    "mf6_msw_recharge_map": "exchanges/rchindex2svat.dxc",
                }
            ],
        },
    }
    with open(tmp_path_dev / "imod_coupler.toml", "wb") as f:
        tomli_w.dump(coupler_toml, f)


def write_ribamod_toml(
    tmp_path_dev: str | Path,
    modflow6_dll: str | Path,
    modflow6_model_dir: str | Path,
    ribasim_dll: str | Path,
    ribasim_dll_dependency: str | Path,
    ribasim_config_file: str | Path,
) -> None:
    """
    Write .toml file which configures the imod coupler run.
    Parameters
    ----------
    directory: str or Path
        Directory in which to write the .toml file.
    modflow6_dll: str or Path
        Path to modflow6 .dll. You can obtain this library by downloading
        `the last iMOD5 release
        <https://oss.deltares.nl/web/imod/download-imod5>`_
    metaswap_dll: str or Path
        Path to metaswap .dll. You can obtain this library by downloading
        `the last iMOD5 release
        <https://oss.deltares.nl/web/imod/download-imod5>`_
    metaswap_dll_dependency: str or Path
        Directory with metaswap .dll dependencies. Directory should contain:
        [fmpich2.dll, mpich2mpi.dll, mpich2nemesis.dll, TRANSOL.dll]. You
        can obtain these by downloading `the last iMOD5 release
        <https://oss.deltares.nl/web/imod/download-imod5>`_
    coupling_dict: dict
        Dictionary with names of coupler packages and paths to mappings.
    """
    coupler_toml = {
        "timing": False,
        "log_level": "INFO",
        "driver_type": "ribamod",
        "driver": {
            "kernels": {
                "modflow6": {
                    "dll": str(modflow6_dll),
                    "work_dir": str(modflow6_model_dir),
                },
                "ribasim": {
                    "dll": str(ribasim_dll),
                    "dll_dep_dir": str(ribasim_dll_dependency),
                    "config_file": str(ribasim_config_file),
                },
            },
            "coupling": [
                {
                    "mf6_model": "GWF_1",
                    "mf6_active_river_packages": {"riv-1": "exchanges/riv-1.tsv"},
                    "mf6_passive_river_packages": {},
                    "mf6_active_drainage_packages": {},
                    "mf6_passive_drainage_packages": {},
                }
            ],
        },
    }
    with open(tmp_path_dev / "imod_coupler.toml", "wb") as f:
        tomli_w.dump(coupler_toml, f)


def write_ribametamod_toml(
    tmp_path_dev: str | Path,
    modflow6_dll: str | Path,
    modflow6_model_dir: str | Path,
    metaswap_dll: str | Path,
    metaswap_dll_dependency: str | Path,
    metaswap_model_dir: str | Path,
    ribasim_dll: str | Path,
    ribasim_dll_dependency: str | Path,
    ribasim_config_file: str | Path,
) -> None:
    """
    Write .toml file which configures the imod coupler run.
    Parameters
    ----------
    directory: str or Path
        Directory in which to write the .toml file.
    modflow6_dll: str or Path
        Path to modflow6 .dll. You can obtain this library by downloading
        `the last iMOD5 release
        <https://oss.deltares.nl/web/imod/download-imod5>`_
    metaswap_dll: str or Path
        Path to metaswap .dll. You can obtain this library by downloading
        `the last iMOD5 release
        <https://oss.deltares.nl/web/imod/download-imod5>`_
    metaswap_dll_dependency: str or Path
        Directory with metaswap .dll dependencies. Directory should contain:
        [fmpich2.dll, mpich2mpi.dll, mpich2nemesis.dll, TRANSOL.dll]. You
        can obtain these by downloading `the last iMOD5 release
        <https://oss.deltares.nl/web/imod/download-imod5>`_
    coupling_dict: dict
        Dictionary with names of coupler packages and paths to mappings.
    """
    coupler_toml = {
        "timing": False,
        "log_level": "INFO",
        "driver_type": "metamod",
        "driver": {
            "kernels": {
                "modflow6": {
                    "dll": str(modflow6_dll),
                    "work_dir": str(modflow6_model_dir),
                },
                "metaswap": {
                    "dll": str(metaswap_dll),
                    "work_dir": str(metaswap_model_dir),
                    "dll_dep_dir": str(metaswap_dll_dependency),
                },
                "ribasim": {
                    "dll": str(ribasim_dll),
                    "dll_dep_dir": str(ribasim_dll_dependency),
                    "config_file": str(ribasim_config_file),
                },
            },
            "coupling": [
                {
                    "enable_sprinkling": False,
                    "mf6_model": "GWF_1",
                    "mf6_msw_recharge_pkg": "rch_msw",
                    "mf6_msw_node_map": "exchanges/nodenr2svat.dxc",
                    "mf6_msw_recharge_map": "exchanges/rchindex2svat.dxc",
                    "mf6_active_river_packages": {"riv-1": "exchanges/riv-1.tsv"},
                    "mf6_passive_river_packages": {},
                    "mf6_active_drainage_packages": {},
                    "mf6_passive_drainage_packages": {},
                },
            ],
        },
    }
    with open(tmp_path_dev / "imod_coupler.toml", "wb") as f:
        tomli_w.dump(coupler_toml, f)


def fill_para_sim_template(msw_folder: Path, path_unsat_dbase: Path) -> None:
    """
    Fill para_sim.inp template in the folder with the path to the unsaturated
    zone database.
    """
    template_file = msw_folder / "para_sim_template.inp"
    if not template_file.exists():
        raise ValueError(f"could not find file {template_file}")
    with open(msw_folder / "para_sim_template.inp") as f:
        para_sim_text = f.read()

    para_sim_text = para_sim_text.replace("{{unsat_path}}", f"{path_unsat_dbase}\\")

    with open(msw_folder / "para_sim.inp", mode="w") as f:
        f.write(para_sim_text)
