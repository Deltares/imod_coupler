import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import tomli_w
from numpy.testing import assert_allclose


def write_toml(
    toml_path: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
):
    coupling_dict = {
        "mf6_model": "GWF_1",
        "mf6_msw_node_map": "./NODENR2SVAT.DXC",
        "mf6_msw_recharge_pkg": "rch_msw",
        "mf6_msw_recharge_map": "./RCHINDEX2SVAT.DXC",
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
                    "work_dir": ".",
                },
                "metaswap": {
                    "dll": str(metaswap_dll_devel),
                    "work_dir": ".\\msw",
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


def test_modstrip_data_present(modstrip_loc):
    """
    Test if modstrip data is not deleted or moved by accident
    """
    input_dir = modstrip_loc / "input"
    results_dir = modstrip_loc / "results"

    assert input_dir.exists()
    assert results_dir.exists()


def test_modstrip_model(
    modstrip_loc,
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

    shutil.copytree(modstrip_loc / "input", tmp_path, dirs_exist_ok=True)

    fill_para_sim_template(tmp_path / "msw", metaswap_lookup_table)

    toml_path = tmp_path / "imod_coupler.toml"

    write_toml(
        toml_path,
        metaswap_dll_devel,
        metaswap_dll_dep_dir_devel,
        modflow_dll_devel,
    )

    subprocess.run([imod_coupler_exec_devel, toml_path], check=True)

    headfile = tmp_path / "GWF_1" / "MODELOUTPUT" / "HEAD" / "HEAD.HED"
    cbcfile = tmp_path / "GWF_1" / "MODELOUTPUT" / "BUDGET" / "BUDGET.CBC"
    msw_csv = tmp_path / "msw" / "msw" / "csv" / "svat_dtgw_0000000001.csv"

    assert headfile.exists()
    assert cbcfile.exists()
    assert msw_csv.exists()

    # If computation failed, Modflow6 usually writes a headfile and cbcfile of 0
    # bytes.
    assert headfile.stat().st_size > 0
    assert cbcfile.stat().st_size > 0
    assert msw_csv.stat().st_size > 0

    # Read msw output and validation data
    data_original = np.loadtxt(modstrip_loc / "results" / "mf2005.txt")
    data_2020_regression = np.loadtxt(modstrip_loc / "results" / "mf6_2020.txt")
    data_develop = pd.read_csv(msw_csv, skipinitialspace=True)

    # The original comparison data compared results for a longer time period
    # (~30 years), whereas our test runs 3 years now. Hence this selection
    nrows = data_develop.shape[0]
    lvgw_original = data_original[:nrows, 0]
    lvgw_2020_regression = data_2020_regression[:nrows, 0]

    vsim_original = data_original[:nrows, 2]
    vsim_2020_regression = data_2020_regression[:nrows, 2]

    lvgw = data_develop["Hgw(m)"]
    # Compute vsim by converting to mm to m3
    svat_area = 1.0e4  # m2
    vsim = data_develop["qsim(mm)"] / 1.0e3 * svat_area

    # Compare fluxes exchanged between modflow and metaswap
    criterion_q = 0.045  # 4.5%
    criterion_h = 0.001  # 1 mm

    assert total_flux_error(vsim_2020_regression, vsim_original) < criterion_q
    assert total_flux_error(vsim, vsim_2020_regression) < criterion_q
    assert total_flux_error(vsim, vsim_original) < criterion_q

    # Compare heads computed by MetaSWAP
    assert_allclose(lvgw_original, lvgw_2020_regression, atol=criterion_h)
    assert_allclose(lvgw, lvgw_original, atol=criterion_h)
    assert_allclose(lvgw, lvgw_2020_regression, atol=criterion_h)
