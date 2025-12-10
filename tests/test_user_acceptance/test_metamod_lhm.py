"""
LHM user acceptance , these are pytest-marked with 'user_acceptance'.

These require the LHM model to be available on the local drive. The test plan
describes how to set this up.
"""

import os
import sys
from pathlib import Path

import pandas as pd
import pytest

import imod
from imod.formats.prj.prj import open_projectfile_data
from imod.logging.config import LoggerType
from imod.logging.loglevel import LogLevel
from imod.mf6.ims import Solution
from imod.mf6.oc import OutputControl
from imod.mf6.simulation import Modflow6Simulation

from typing import Callable

from primod import MetaMod, MetaModDriverCoupling

def convert_imod5_to_mf6_sim(imod5_data: dict, period_data: dict, times: list) -> Modflow6Simulation:
    simulation = Modflow6Simulation.from_imod5_data(
        imod5_data,
        period_data,
        times,
    )
    simulation.set_validation_settings(imod.mf6.ValidationSettings(ignore_time=True))
    # Set settings so that the simulation behaves like iMOD5
    simulation["imported_model"]["oc"] = OutputControl(
        save_head="last", save_budget="last"
    )
    # Mimic iMOD5's "Moderate" settings
    solution = Solution(
        modelnames=["imported_model"],
        print_option="summary",
        outer_csvfile=None,
        inner_csvfile=None,
        no_ptc=None,
        outer_dvclose=0.001,
        outer_maximum=150,
        under_relaxation="dbd",
        under_relaxation_theta=0.9,
        under_relaxation_kappa=0.0001,
        under_relaxation_gamma=0.0,
        under_relaxation_momentum=0.0,
        backtracking_number=0,
        backtracking_tolerance=0.0,
        backtracking_reduction_factor=0.0,
        backtracking_residual_limit=0.0,
        inner_maximum=30,
        inner_dvclose=0.001,
        inner_rclose=100.0,
        rclose_option="strict",
        linear_acceleration="bicgstab",
        relaxation_factor=0.97,
        preconditioner_levels=0,
        preconditioner_drop_tolerance=0.0,
        number_orthogonalizations=0,
    )
    simulation["ims"] = solution

    simulation["imported_model"]["npf"]["xt3d_option"] = True

    return simulation


def cleanup_mf6_sim(simulation: Modflow6Simulation) -> None:
    """
    Cleanup the simulation of erronous package data
    """
    model = simulation["imported_model"]
    for pkg in model.values():
        pkg.dataset.load()

    mask = model.domain
    simulation.mask_all_models(mask)
    dis = model["dis"]

    pkgs_to_cleanup = [
        "riv-1riv",
        "riv-1drn",
        "riv-2riv",
        "riv-2drn",
        "riv-3riv",
        "riv-3drn",
        "riv-4riv",
        "riv-4drn",
        "riv-5riv",
        "riv-5drn",
        "drn-1",
        "drn-2",
        "drn-3",
        "ghb",
    ]

    for pkgname in pkgs_to_cleanup:
        if pkgname in model.keys():
            model[pkgname].cleanup(dis)

    wel_keys = [key for key in model.keys() if "wel-" in key]
    # Account for edge case where iMOD5 allocates to left-hand column of edge,
    # and iMOD Python to right-hand.
    for pkgname in wel_keys:
        model[pkgname].dataset["x"] -= 1e-10

    for pkgname in wel_keys:
        model[pkgname].cleanup(dis)

    # Save flows
    topsystems = [
        key
        for key in model.keys()
        if ("riv-" in key) | ("drn-" in key) | ("ghb-" in key)
    ]
    for pkgname in topsystems:
        model[pkgname].dataset["save_flows"] = True
    model["npf"].dataset["save_flows"] = True

def convert_imod5_to_msw_model(
    imod5_data: dict, mf6_sim: Modflow6Simulation, times: list
) -> imod.msw.MetaSwapModel:
    dis_pkg = mf6_sim["imported_model"]["dis"]
    msw_model = imod.msw.MetaSwapModel.from_imod5_data(imod5_data, dis_pkg, times)
    msw_model["oc"] = imod.msw.VariableOutputControl()

    return msw_model

def import_lhm_mf6_and_msw():
    """
    Convert iMOD5 LHM model to MODFLOW 6 using imod-python
    """
    user_acceptance_dir = Path(os.environ["USER_ACCEPTANCE_DIR"])
    lhm_dir = user_acceptance_dir / "LHM_transient"
    lhm_prjfile = lhm_dir / "model" / "LHM_transient_test.PRJ"
    logfile_path = lhm_dir / "logfile_mf6.txt"

    out_dir = lhm_dir / "mf6_imod-python"
    out_dir.mkdir(parents=True, exist_ok=True)

    # notes: M/D/Y and convert to list of datetime.
    times = pd.date_range(start="1/1/2011", end="1/1/2012", freq="D").tolist()
    #    os.chdir(lhm_dir)

    with open(logfile_path, "w") as sys.stdout:
        imod.logging.configure(
            LoggerType.PYTHON,
            log_level=LogLevel.DEBUG,
            add_default_file_handler=False,
            add_default_stream_handler=True,
        )
        # Read iMOD5 project file data
        imod5_data, period_data = open_projectfile_data(lhm_prjfile)

        # Convert to MODFLOW 6 simulation and cleanup
        mf6_simulation = convert_imod5_to_mf6_sim(imod5_data, period_data, times)
        cleanup_mf6_sim(mf6_simulation)

        # Convert to MetaSwap model
        msw_model = convert_imod5_to_msw_model(imod5_data, mf6_simulation, times)

    return mf6_simulation, msw_model

@pytest.fixture(scope="session", autouse=False)
def lhm_coupling():
    """
    Test coupling of LHM MODFLOW 6 and MetaSwap models
    """
    mf6_simulation, msw_model = import_lhm_mf6_and_msw()

    driver_coupling = MetaModDriverCoupling(
        mf6_model="imported_model", mf6_recharge_package="msw-rch", mf6_wel_package="msw-sprinkling"
    )
    return MetaMod(
        msw_model,
        mf6_simulation,
        coupling_list=[driver_coupling],
    )

@pytest.fixture(scope="session", autouse=False)
def written_lhm_conversion(
    tmp_path_factory: Path,
    lhm_coupling: MetaMod,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    modflow_dll_devel: Path,
):
    """
    Write LHM conversion to temporary path
    """
    tmp_path = tmp_path_factory.mktemp("test_lhm_conversion")
    metamod_model = lhm_coupling

    metamod_model.write(
        tmp_path,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
    )

    return tmp_path

@pytest.mark.user_acceptance
def test_lhm_metamod(
    lhm_coupling: MetaMod,
):
    """
    Test if the lhm_driver_coupling fixture works
    """
    assert isinstance(lhm_coupling, MetaMod)
    
    driver_coupling = lhm_coupling.coupling_list[0]
    assert isinstance(driver_coupling, MetaModDriverCoupling)
    assert driver_coupling._check_sprinkling() == True

    mf6_simulation = lhm_coupling.mf6_simulation
    gwf_model = mf6_simulation[driver_coupling.mf6_model]
    msw_model = lhm_coupling.msw_model

    grid_mapping, rch_mapping, well_mapping = driver_coupling.derive_mapping(
        msw_model=msw_model,
        gwf_model=gwf_model,
    )

    grid_mapping.dataset["svat"].shape == (2, 1300, 1200)
    grid_mapping.dataset["mod_id"].shape == (2, 1300, 1200)
    rch_mapping.dataset["svat"].shape == (2, 1300, 1200)
    rch_mapping.dataset["rch_id"].shape == (2, 1300, 1200)
    well_mapping.dataset["svat"].shape == (2, 1300, 1200)
    # Check if well mappings are 1d arrays
    assert len(well_mapping.dataset["wel_id"].shape) == 1
    assert len(well_mapping.dataset["svat"].shape) == 1


@pytest.mark.user_acceptance
def test_lhm_written_files(
    written_lhm_conversion: Path,
) -> None:
    """
    Test if written dxc files are as expected
    """
    dxc_paths= list((written_lhm_conversion / "exchanges").glob("*.dxc"))
    dxc_filenames = [p.name.lower() for p in dxc_paths]
    assert len(dxc_filenames) == 3
    expected_dxc_filenames = {
        "nodenr2svat.dxc",
        "rchindex2svat.dxc",
        "wellindex2svat.dxc",
    }
    assert set(dxc_filenames) == expected_dxc_filenames

    path_nodenr2svat = written_lhm_conversion / "exchanges" / "nodenr2svat.dxc"
    path_rchindex2svat = written_lhm_conversion / "exchanges" / "rchindex2svat.dxc"
    path_wellindex2svat = written_lhm_conversion / "exchanges" / "wellindex2svat.dxc"

    settings = dict(delimiter= '\s+', index_col=False)
    columns = ["node", "svat", "layer"]
    columns_bc = ["bc_index", "svat", "layer"]

    # Test nodenr2svat.dxc
    df_nodenr2svat = pd.read_csv(path_nodenr2svat, names=columns, **settings)
    # nodenr should not exceed node number beyond layer one
    assert df_nodenr2svat["node"].max() <= (1300 * 1200)
    # First active nodes are located in the sea, should not be connected to
    # svats
    assert df_nodenr2svat["node"].min() > 1
    # Svat should start counting at 1
    assert df_nodenr2svat["svat"].min() == 1
    # Less than half of the model domain is expected to be covered by
    # svats
    assert df_nodenr2svat["svat"].max() <= ((1300 * 1200) / 2)
    # Layer should be 1 for all entries
    assert (df_nodenr2svat["layer"] == 1).all()

    # Test rchindex2svat.dxc
    df_rchindex2svat = pd.read_csv(path_rchindex2svat, names=columns_bc, **settings)
    # Rch index and svat should start at 1
    assert df_rchindex2svat["bc_index"].min() == 1
    assert df_rchindex2svat["svat"].min() == 1
    # rch index should be equal to svat in this model
    assert (df_rchindex2svat["svat"] == df_rchindex2svat["bc_index"]).all()
    # svat max should be equal to nodenr2svat max
    assert df_rchindex2svat["svat"].max() == df_nodenr2svat["svat"].max()
    # Layer should be 1 for all entries
    assert (df_rchindex2svat["layer"] == 1).all()

    # Test wellindex2svat.dxc
    df_wellindex2svat = pd.read_csv(path_wellindex2svat, names=columns_bc, **settings)
    # There should be wells present in layers other than 1
    assert (df_wellindex2svat["layer"] > 1).any()
    # Well svat should not exceed nodenr2svat svat
    assert df_wellindex2svat["svat"].max() <= df_nodenr2svat["svat"].max()
    # There should be less wells than recharge cells
    assert df_wellindex2svat["bc_index"].max() <= df_rchindex2svat["bc_index"].max()



@pytest.mark.user_acceptance
def test_lhm_coupled_simulation(
    written_lhm_conversion: Path,
    run_coupler_function: Callable[[Path], None],
) -> None:
    """
    Test LHM iMOD5 to MODFLOW 6 conversion
    """
    toml_path = written_lhm_conversion / MetaMod._toml_name

    run_coupler_function(toml_path)

    # Test if MetaSWAP output written
    assert len(list(( written_lhm_conversion / "MetaSWAP").glob("*/*.idf"))) > 0

    # Test if Modflow6 output written
    headfile =  written_lhm_conversion / "Modflow6" / "imported_model" / "imported_model.hds"
    cbcfile =  written_lhm_conversion / "Modflow6" / "imported_model" / "imported_model.cbc"

    assert headfile.exists()
    assert cbcfile.exists()
    # If computation failed, Modflow6 usually writes a headfile and cbcfile of 0
    # bytes.
    assert headfile.stat().st_size > 0
    assert cbcfile.stat().st_size > 0