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

    assert headfile.exists()
    assert cbcfile.exists()
    assert msw_csv.exists()

    # If computation failed, Modflow6 usually writes a headfile and cbcfile of 0
    # bytes.
    assert headfile.stat().st_size > 0
    assert cbcfile.stat().st_size > 0
    assert msw_csv.stat().st_size > 0

    for isvat in np.arange(371):
        # Read msw output and validation data
        data_2023_regression = np.loadtxt(
            modstrip_full_range_dbase_loc
            / "results"
            / "svat_dtgw_{:010d}.csv".format(isvat + 1)
        )
        msw_csv = (
            tmp_path / "msw" / "msw" / "csv" / "svat_dtgw_{:010d}.csv".format(isvat + 1)
        )
        data_develop = pd.read_csv(msw_csv, skipinitialspace=True)

        # convert to coupling balans terms
        qmodf = data_develop["qmodf(mm)"] / 1000 * data_develop["area(m2)"]
        qmsw = data_develop["qsim(mm)"] / 1000 * data_develop["area(m2)"]
        qmsw_cor = data_develop["qsimcorrmf(mm)"] / 1000 * data_develop["area(m2)"]
        dhgw = data_develop["dHgw(m)"]
        hgw = data_develop["Hgw(m)"]
        hgw_mod = data_develop["Hgwmodf(m)"]
        sc1 = data_develop["sc1(m3/m2/m)"] * data_develop["area(m2)"]

        # get reference values
        qmodf_ref = (
            data_2023_regression["qmodf(mm)"] / 1000 * data_2023_regression["area(m2)"]
        )
        qmsw_ref = (
            data_2023_regression["qsim(mm)"] / 1000 * data_2023_regression["area(m2)"]
        )
        hgw_ref = data_2023_regression["dHgw(m)"]

        # mf6 data
        head_mf6 = imod.mf6.open_hds(headfile, grbfile, False)
        flux_mf6 = imod.mf6.open_cbc(cbcfile, grbfile, False)

        # criterion
        criterion_q = 0.001  # %
        criterion_q_ref = 0.0001  # %

        # --- check coupling concept ---

        # coupling balanse of MF6-MSW is defined as:
        # qsim + qmodf = dHgw * sc1

        # CHECK 1: evaluate absolute value of qsim to reference
        # if assert exception; metaswap internal flux is changed, possible conceptual changes in MetaSwap
        assert total_flux_error(qmsw, qmsw_ref) < criterion_q_ref

        # CHECK 2: evaluate absolute value of qmodf to reference
        # if assert exception; modflow internal flux is changed, possible conceptual changes in MODFLOW
        assert total_flux_error(qmodf, qmodf_ref) < criterion_q_ref

        # CHECK 3: evaluate full coupling balance
        lhs = (qmodf + qmsw) / data_develop["area(m2)"] * 1000  # mm
        rhs = (dhgw * sc1) / data_develop["area(m2)"] * 1000  # mm

        assert total_flux_error(lhs, rhs) < criterion_q

        # CHECK 4: evaluate if non-convergentie is corrected by correction flux
        # we cant use the difference betwee hgw and hgw_mod, check with Paul how to evaluate this

        # CHECK 5: evaluate absolute value of hgw to reference
        assert total_flux_error(hgw, hgw_ref) < criterion_q_ref

        # --- check correctness of coupling ---

        # CHECK 1: evaluate if sum of RCH (mf6) is equal to qmsw (msw)
        assert (
            total_flux_error(flux_mf6["rch_msw"][:, 0, isvat, 0].values, qmsw)
            < criterion_q
        )

        # CHECK 2: evaluate if head of mf6-cel is equal to head of msw-svat (this cases 1-1 coupling)
        assert total_flux_error(head_mf6[:, 0, isvat, 0].values, hgw) < criterion_q
        # assert_allclose(lvgw_original, lvgw_2020_regression, atol=criterion_h)

        # CHECK 3: evaluate if STO (mf6) is equal to SC1 (MSW)
        # MF6 does not have STO as output variable, so we compute it from Q-STO and dH
        dh_insert = -5.0 - head_mf6[0, 0, isvat, 0]  # dh relative to ic
        dh_mf6 = np.insert(-np.diff(head_mf6[:, 0, isvat, 0].values), 0, dh_insert)
        sc1_mf6 = flux_mf6["sto-ss"][:, 0, isvat, 0].values / (dh_mf6 * 100**2)
        assert total_flux_error(data_develop["sc1(m3/m2/m)"], sc1_mf6) < criterion_q
