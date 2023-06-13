import shutil
import subprocess
from pathlib import Path
from typing import Union

import imod
import numpy as np
import pandas as pd
import tomli_w
import xarray as xr
from numpy.testing import assert_allclose

from imod_coupler.__main__ import run_coupler


def write_toml(
    toml_path: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
):
    coupling_dict = dict(
        mf6_model="GWF_1",
        mf6_msw_node_map="./NODENR2SVAT.DXC",
        mf6_msw_recharge_pkg="rch_msw",
        mf6_msw_recharge_map="./RCHINDEX2SVAT.DXC",
        enable_sprinkling=False,
    )

    coupler_toml = {
        "timing": False,
        "log_level": "INFO",
        "log_file": "imod_coupler.log",
        "driver_type": "metamod",
        "driver": {
            "kernels": {
                "modflow6": {
                    "dll": str(modflow_dll_devel),
                    "work_dir": ".",
                },
                "metaswap": {
                    "dll": str(metaswap_dll_devel),
                    "work_dir": f".\\msw",
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


def total_flux_error(
    q_test: Union[np.ndarray, xr.DataArray, xr.Dataset],
    q_ref: Union[np.ndarray, xr.DataArray, xr.Dataset],
) -> np.array:
    """
    Computes total relative flux error compared to a reference flux.
    shape of input arrays = time, row, col
    """
    if isinstance(q_test, xr.DataArray):
        q_test = q_test.values
    if isinstance(q_ref, xr.DataArray):
        q_ref = q_ref.values
    return np.squeeze(
        np.sum(np.abs(q_test - q_ref), axis=0) / np.sum(np.abs(q_ref), axis=0)
    )


def test_modstrip_data_present(modstrip_full_range_dbase_loc):
    """
    Test if modstrip data is not deleted or moved by accident
    """
    input_dir = modstrip_full_range_dbase_loc / "input"
    results_dir = modstrip_full_range_dbase_loc / "results"

    assert input_dir.exists()
    assert results_dir.exists()


def test_modstrip_model(
    modstrip_full_range_dbase_loc,
    tmp_path,
    metaswap_lookup_table,
    imod_coupler_exec_devel,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
):
    """
    Run modstrip model and test output, compare with results of previous
    comparison in 2020.
    """

    shutil.copytree(
        modstrip_full_range_dbase_loc / "input", tmp_path, dirs_exist_ok=True
    )

    fill_para_sim_template(tmp_path / "msw", metaswap_lookup_table)

    toml_path = tmp_path / "imod_coupler.toml"

    write_toml(
        toml_path,
        metaswap_dll_devel,
        metaswap_dll_dep_dir_devel,
        modflow_dll_devel,
    )

    # subprocess.run([imod_coupler_exec_devel, toml_path], check=True)
    run_coupler(toml_path)
    headfile = tmp_path / "GWF_1" / "MODELOUTPUT" / "HEAD" / "HEAD.HED"
    cbcfile = tmp_path / "GWF_1" / "MODELOUTPUT" / "BUDGET" / "BUDGET.CBC"
    grbfile = tmp_path / "GWF_1" / "MODELINPUT" / "MS_MF6.DIS6.grb"

    log_path = toml_path.parent / "logfile.csv"

    assert headfile.exists()
    assert cbcfile.exists()

    # if computation failed, Modflow6 usually writes a headfile and cbcfile of 0
    # bytes.
    assert headfile.stat().st_size > 0
    assert cbcfile.stat().st_size > 0

    # read msw output
    area = imod.idf.open(tmp_path / "msw" / "bdgqmodf" / "area_L1.IDF").isel(
        layer=0, drop=True
    )
    qmodf = imod.idf.open(tmp_path / "msw" / "bdgqmodf" / "bdgqmodf_*_L1.IDF").isel(
        layer=0, drop=True
    )
    qmsw = imod.idf.open(tmp_path / "msw" / "msw_qsim" / "msw_qsim_*_L1.IDF").isel(
        layer=0, drop=True
    )
    # qmsw_cor = imod.idf.open(tmp_path / "msw" / "msw_qsimcorrmf" / "bdgqsimcorrmf_*_L1.IDF")
    hgw = imod.idf.open(tmp_path / "msw" / "msw_Hgw" / "msw_Hgw_*_L1.IDF").isel(
        layer=0, drop=True
    )
    dhgw = hgw.diff("time")
    hgw_mod = imod.idf.open(
        tmp_path / "msw" / "msw_Hgwmodf" / "msw_Hgwmodf_*_L1.IDF"
    ).isel(layer=0, drop=True)
    sc1 = imod.idf.open(tmp_path / "msw" / "msw_sc1" / "msw_sc1_*_L1.IDF").isel(
        layer=0, drop=True
    )

    # reference output
    qmodf_ref = imod.idf.open(
        modstrip_full_range_dbase_loc / "results" / "bdgqmodf" / "bdgqmodf_*_L1.IDF"
    ).isel(layer=0, drop=True)
    qmsw_ref = imod.idf.open(
        modstrip_full_range_dbase_loc / "results" / "msw_qsim" / "msw_qsim_*_L1.IDF"
    ).isel(layer=0, drop=True)
    hgw_ref = imod.idf.open(
        modstrip_full_range_dbase_loc / "results" / "msw_Hgw" / "msw_Hgw_*_L1.IDF"
    ).isel(layer=0, drop=True)

    # read mf6 output
    head_mf6 = imod.mf6.open_hds(headfile, grbfile, False)
    flux_mf6 = imod.mf6.open_cbc(cbcfile, grbfile, False)

    # evaluation criterion
    criterion_wbal = 0.0002  # mm
    criterion_head = 0.0001  # mm
    criterion_q = 0.0001  # %

    # first write to logfile
    log = np.zeros(372 * 7, dtype=float).reshape((7, 372))

    # CHECK 1: evaluate absolute value of qsim to reference
    # if assert exception; metaswap internal flux is changed, possible conceptual changes in MetaSwap
    log[0, :] = total_flux_error(qmsw, qmsw_ref)

    # CHECK 2: evaluate absolute value of qmodf to reference
    # if assert exception; modflow internal flux is changed, possible conceptual changes in MODFLOW
    log[1, :] = total_flux_error(qmodf, qmodf_ref)

    # CHECK 3: evaluate full coupling balance
    dh_insert = head_mf6.isel(layer=0, time=0).values - -5.0
    dhgw = np.insert(
        np.diff(head_mf6.isel(layer=0).values, axis=0), 0, dh_insert, axis=0
    )
    lhs = (qmodf + qmsw) * 1000  # mm
    rhs = (dhgw * sc1.values) * 1000  # mm
    log[2, :] = np.squeeze(np.amax(np.abs(lhs.values - rhs), axis=0))

    # CHECK 4: evaluate if non-convergentie is corrected by correction flux
    # we cant use the difference betwee hgw and hgw_mod, check with Paul how to evaluate this

    # CHECK 5: evaluate absolute value of hgw to reference
    log[3, :] = np.squeeze(np.amax(np.abs(hgw.values - hgw_ref.values), axis=0))

    # --- check correctness of coupling ---

    # CHECK 1: evaluate if sum of RCH (mf6) is equal to qmsw (msw)
    log[4, :] = total_flux_error(flux_mf6["rch_msw"].isel(layer=0) / (100 * 100), qmsw)

    # CHECK 2: evaluate if head of mf6-cel is equal to head of msw-svat (this cases 1-1 coupling)
    log[5, :] = np.squeeze(
        np.amax(np.abs(head_mf6.isel(layer=0).values - hgw.values), axis=0)
    )

    # CHECK 3: evaluate if STO (mf6) is equal to SC1 (MSW)
    # MF6 does not have STO as output variable, so we compute it from Q-STO and dH
    sc1_mf6 = -flux_mf6["sto-ss"].isel(layer=0).values / (dhgw * 100**2)
    log[6, :] = np.squeeze(np.amax(np.abs(sc1.values - sc1_mf6), axis=0))

    # write logfile
    np.savetxt(log_path, log, fmt="%1.5f", newline="\n")

    # do asserts
    assert any(log[0, :] < criterion_q)
    assert any(log[1, :] < criterion_q)
    assert any(log[2, :] < criterion_wbal)
    assert any(log[3, :] < criterion_head)
    assert any(log[4, :] < criterion_q)
    assert any(log[5, :] < criterion_head)
    assert any(log[6, :] < criterion_head)
