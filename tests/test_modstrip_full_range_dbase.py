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


def total_flux_error(q_test, q_ref):
    """
    Computes total relative flux error compared to a reference flux.
    """
    return np.abs(q_test - q_ref).sum() / np.abs(q_ref).sum()


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
    area = imod.idf.open(tmp_path / "msw" / "bdgqmodf" / "area_L1.IDF")
    qmodf = imod.idf.open(tmp_path / "msw" / "bdgqmodf" / "bdgqmodf_*_L1.IDF") * area
    qmsw = imod.idf.open(tmp_path / "msw" / "msw_qsim" / "msw_qsim_*_L1.IDF") * area
    # qmsw_cor = imod.idf.open(tmp_path / "msw" / "msw_qsimcorrmf" / "bdgqsimcorrmf_*_L1.IDF") * area
    hgw = imod.idf.open(tmp_path / "msw" / "msw_Hgw" / "msw_Hgw_*_L1.IDF")
    dhgw = hgw.diff("time")
    hgw_mod = imod.idf.open(tmp_path / "msw" / "msw_Hgwmodf" / "msw_Hgwmodf_*_L1.IDF")
    sc1 = imod.idf.open(tmp_path / "msw" / "msw_sc1" / "msw_sc1_*_L1.IDF") * area

    # reference output
        qmodf_ref = (
            data_2023_regression["qmodf(mm)"] / 1000 * data_2023_regression["area(m2)"]
        )
        qmsw_ref = (
            data_2023_regression["qsim(mm)"] / 1000 * data_2023_regression["area(m2)"]
        )
        hgw_ref = data_2023_regression["Hgw(m)"]

    # read mf6 output
    head_mf6 = imod.mf6.open_hds(headfile, grbfile, False)
    flux_mf6 = imod.mf6.open_cbc(cbcfile, grbfile, False)

    # evaluation criterion
    criterion_q = 0.001  # %          ! compare waterbalanse of run
    criterion_q_ref = 0.0001  # %      ! compare to reference

    # log array
    log = np.empty(371 * 7, dtype=bool).reshape((7, 371))
    for isvat in np.arange(371):
        print("reading files svat {isvat}".format(isvat=isvat))
        # read msw output and reference data
        msw_csv = (
            tmp_path / "msw" / "msw" / "csv" / "svat_dtgw_{:010d}.csv".format(isvat + 1)
        )
        msw_csv_regression = (
            modstrip_full_range_dbase_loc
            / "results"
            / "svat_dtgw_{:010d}.csv".format(isvat + 1)
        )

        data_2023_regression = pd.read_csv(msw_csv_regression, skipinitialspace=True)
        assert msw_csv.exists()
        assert msw_csv.stat().st_size > 0
        data_develop = pd.read_csv(msw_csv, skipinitialspace=True)

        # convert to coupling balans terms
        qmodf = data_develop["qmodf(mm)"] / 1000 * data_develop["area(m2)"]
        qmsw = data_develop["qsim(mm)"] / 1000 * data_develop["area(m2)"]
        qmsw_cor = data_develop["qsimcorrmf(mm)"] / 1000 * data_develop["area(m2)"]
        dhgw = data_develop["dHgw(m)"]
        hgw = data_develop["Hgw(m)"]
        hgw_mod = data_develop["Hgwmodf(m)"]
        sc1 = data_develop["sc1(m3/m2/m)"] * data_develop["area(m2)"]

        # reference data
        qmodf_ref = (
            data_2023_regression["qmodf(mm)"] / 1000 * data_2023_regression["area(m2)"]
        )
        qmsw_ref = (
            data_2023_regression["qsim(mm)"] / 1000 * data_2023_regression["area(m2)"]
        )
        hgw_ref = data_2023_regression["Hgw(m)"]

        # --- check coupling concept ---

        # coupling balanse of MF6-MSW is defined as:
        # qsim + qmodf = dHgw * sc1

        # CHECK 1: evaluate absolute value of qsim to reference
        # if assert exception; metaswap internal flux is changed, possible conceptual changes in MetaSwap
        log[0, isvat] = total_flux_error(qmsw, qmsw_ref)

        # CHECK 2: evaluate absolute value of qmodf to reference
        # if assert exception; modflow internal flux is changed, possible conceptual changes in MODFLOW
        log[1, isvat] = total_flux_error(qmodf, qmodf_ref)

        # CHECK 3: evaluate full coupling balance
        lhs = (qmodf + qmsw) / data_develop["area(m2)"] * 1000  # mm
        rhs = (dhgw * sc1) / data_develop["area(m2)"] * 1000  # mm

        log[2, isvat] = total_flux_error(lhs, rhs) < criterion_q

        # CHECK 4: evaluate if non-convergentie is corrected by correction flux
        # we cant use the difference betwee hgw and hgw_mod, check with Paul how to evaluate this

        # CHECK 5: evaluate absolute value of hgw to reference
        log[3, isvat] = total_flux_error(hgw, hgw_ref)

        # --- check correctness of coupling ---

        # CHECK 1: evaluate if sum of RCH (mf6) is equal to qmsw (msw)
        log[4, isvat] = total_flux_error(
            flux_mf6["rch_msw"][:, 0, isvat, 0].values, qmsw
        )

        # CHECK 2: evaluate if head of mf6-cel is equal to head of msw-svat (this cases 1-1 coupling)
        log[5, isvat] = total_flux_error(head_mf6[:, 0, isvat, 0].values, hgw)

        # CHECK 3: evaluate if STO (mf6) is equal to SC1 (MSW)
        # MF6 does not have STO as output variable, so we compute it from Q-STO and dH
        dh_insert = -5.0 - head_mf6[0, 0, isvat, 0]  # dh relative to ic
        dh_mf6 = np.insert(-np.diff(head_mf6[:, 0, isvat, 0].values), 0, dh_insert)
        sc1_mf6 = flux_mf6["sto-ss"][:, 0, isvat, 0].values / (dh_mf6 * 100**2)
        log[6, isvat] = total_flux_error(data_develop["sc1(m3/m2/m)"], sc1_mf6)

    # write logfile
    np.savetxt(log_path, log, fmt="%5i", newline="\n")

    assert any(log)
