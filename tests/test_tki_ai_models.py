import shutil
import subprocess
from pathlib import Path

import imod
import numpy as np
import pandas as pd
import tomli
import tomli_w
from numpy.testing import assert_allclose

from imod_coupler.__main__ import run_coupler
from imod_coupler.drivers.metamod.split_mf6_output import split_heads_file


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
    shutil.copytree(tki_ai_model_local, tmp_path, dirs_exist_ok=True)

    fill_para_sim_template(tmp_path / "MetaSWAP", metaswap_lookup_table)

    toml_path = tmp_path / "imod_coupler.toml"

    run_coupler(toml_path)

    with open(toml_path, "rb") as f:
        toml_dict = tomli.load(f)

    nrepeat = toml_dict["driver"]["coupling"][0]["repeat_period"]
    mf6_work_dir = Path(toml_dict["driver"]["kernels"]["modflow6"]["work_dir"])
    mf6_name = Path(toml_dict["driver"]["coupling"][0]["mf6_model"])

    hds_file = tmp_path / mf6_work_dir / mf6_name / "heads.hds"
    grb_file = tmp_path / mf6_work_dir / mf6_name / "MODELINPUT" / "T-MODEL-F.DIS6.grb"
    out_file = tmp_path / mf6_work_dir / mf6_name / "output" / "model{imodel}"
    ncdf_output = True
    idf_output = True

    split_heads_file(
        "1993-12-31", hds_file, grb_file, nrepeat, out_file, ncdf_output, idf_output
    )
