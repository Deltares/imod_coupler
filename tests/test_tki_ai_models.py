import shutil
import subprocess
from pathlib import Path

import imod
import numpy as np
import pandas as pd
import tomli_w
from numpy.testing import assert_allclose

from imod_coupler.__main__ import run_coupler


def write_toml(
    toml_path: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
):
    coupling_dict = {
        "mf6_model": "GWF_1",
        "mf6_msw_node_map": ".\\exchanges\\NODENR2SVAT.DXC",
        "mf6_msw_recharge_pkg": "rch_msw",
        "mf6_msw_recharge_map": ".\\exchanges\\RCHINDEX2SVAT.DXC",
        "enable_sprinkling": False,
    }

    coupler_toml = {
        "timing": False,
        "log_level": "INFO",
        "log_file": "imod_coupler.log",
        "driver_type": "metamod",
        "driver": {
            "kernels": {
                "modflow6": {
                    "dll": str(modflow_dll_devel),
                    "work_dir": ".\\MODFLOW6",
                },
                "metaswap": {
                    "dll": str(metaswap_dll_devel),
                    "work_dir": ".\\MetaSWAP",
                    "dll_dep_dir": str(metaswap_dll_dep_dir_devel),
                },
            },
            "coupling": [coupling_dict],
        },
    }

    with open(toml_path, "wb") as f:
        tomli_w.dump(coupler_toml, f)


def fill_para_sim_template(msw_folder, path_unsat_dbase):
    """
    Fill para_sim.inp template in the folder with the path to the unsaturated
    zone database.
    """
    with open(msw_folder / "para_sim_template.inp") as f:
        para_sim_text = f.read()

    para_sim_text = para_sim_text.replace("{{unsat_path}}", f"{path_unsat_dbase}\\")

    with open(msw_folder / "para_sim.inp", mode="w") as f:
        f.write(para_sim_text)


def test_tki_ai_model_local(
    tki_ai_model_local: Path,
    tmp_path: Path,
    metaswap_lookup_table: Path,
    imod_coupler_exec_devel: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
) -> None:
    """
    Run modstrip model and test output, compare with results of previous
    comparison in 2020.
    """

    shutil.copytree(tki_ai_model_local, tmp_path, dirs_exist_ok=True)

    fill_para_sim_template(tmp_path / "MetaSWAP", metaswap_lookup_table)

    toml_path = tmp_path / "imod_coupler.toml"

    # write_toml(
    #    toml_path,
    #    metaswap_dll_devel,
    #    metaswap_dll_dep_dir_devel,
    #    modflow_dll_devel,
    # )

    run_coupler(toml_path)

    headfile = tmp_path / "MODFLOW6" / "GWF_1" / "HEAD.HED"
    grbfile = tmp_path / "MODFLOW6" / "GWF_1" / "MODELINPUT" / "T-MODEL-F.DIS6.grb"
    heads = imod.mf6.open_hds(headfile, grbfile, False)
    starttime = pd.to_datetime("1994/01/01")
    timedelta = pd.to_timedelta(heads["time"], "D")
    heads = heads.assign_coords(time=starttime + timedelta)
    imod.idf.save(tmp_path / "MODFLOW6" / "GWF_1" / "head.idf", heads)


def test_tki_ai_model_global(
    tki_ai_model_global: Path,
    tmp_path: Path,
    metaswap_lookup_table: Path,
    imod_coupler_exec_devel: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
) -> None:
    """
    Run modstrip model and test output, compare with results of previous
    comparison in 2020.
    """

    shutil.copytree(tki_ai_model_global, tmp_path, dirs_exist_ok=True)

    fill_para_sim_template(tmp_path / "MetaSWAP", metaswap_lookup_table)

    toml_path = tmp_path / "imod_coupler.toml"

    # write_toml(
    #    toml_path,
    #    metaswap_dll_devel,
    #    metaswap_dll_dep_dir_devel,
    #    modflow_dll_devel,
    # )

    run_coupler(toml_path)

    headfile = tmp_path / "MODFLOW6" / "GWF_1" / "HEAD.HED"
    grbfile = tmp_path / "MODFLOW6" / "GWF_1" / "MODELINPUT" / "T-MODEL-F.DIS6.grb"
    heads = imod.mf6.open_hds(headfile, grbfile, False)
    starttime = pd.to_datetime("1994/01/01")
    timedelta = pd.to_timedelta(heads["time"], "D")
    heads = heads.assign_coords(time=starttime + timedelta)
    imod.idf.save(tmp_path / "MODFLOW6" / "GWF_1" / "head.idf", heads)
