"""
LHM user acceptance , these are pytest-marked with 'user_acceptance'.

These require the LHM model to be available on the local drive. The test plan
describes how to set this up.
"""

import os
import sys
from collections.abc import Callable
from pathlib import Path

import imod
import numpy as np
import pandas as pd
import pytest
from imod.formats.prj.prj import open_projectfile_data
from imod.logging.config import LoggerType
from imod.logging.loglevel import LogLevel
from imod.mf6.ims import Solution
from imod.mf6.oc import OutputControl
from imod.mf6.simulation import Modflow6Simulation
from primod import MetaMod, MetaModDriverCoupling


def read_external_binaryfile(path: Path, dtype: type, max_rows: int) -> np.ndarray:
    return np.fromfile(
        file=path,
        dtype=dtype,
        count=max_rows,
        offset=52,  # skip header (52 bytes)
        sep="",
    )


def read_area_svat(path: Path) -> pd.DataFrame:
    area_svat_dict = imod.msw.fixed_format.fixed_format_parser(
        path, imod.msw.GridData._metadata_dict
    )
    return pd.DataFrame(area_svat_dict)


def coupled_nodes_grid(
    data_idomain_top: np.ndarray, node2svat: pd.DataFrame
) -> tuple[np.ndarray, pd.DataFrame]:
    """
    Create a grid showing which nodes are coupled based on the node2svat mapping
    and the idomain data.

    Parameters
    ----------
    data_idomain_top: 2D array
        idomain data of top layer
    node2svat: pd.DataFrame
        node2svat mapping dataframe, should be zero-based
    """
    is_active = data_idomain_top >= 1
    mod_id = np.zeros_like(data_idomain_top, dtype=np.int32)
    n_active = is_active.sum()
    mod_id[is_active] = np.arange(1, n_active + 1)

    # Due to a bug in iMOD5, also nodes coupled to wells are included in
    # node2svat. Only need to do this for iMOD5 data
    node2svat = node2svat.loc[node2svat["node"] < n_active]

    rows, cols = np.nonzero(mod_id)
    rows_dxc = rows[node2svat["node"].to_numpy()]
    cols_dxc = cols[node2svat["node"].to_numpy()]

    coupled_nodes = np.zeros_like(mod_id, dtype=np.int32)
    coupled_nodes[rows_dxc, cols_dxc] = 1

    node2svat["row"] = rows_dxc
    node2svat["col"] = cols_dxc

    return coupled_nodes, node2svat


def convert_imod5_to_mf6_sim(
    imod5_data: dict, period_data: dict, times: list
) -> Modflow6Simulation:
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
    solution = Solution(
        modelnames=["imported_model"],
        print_option="summary",
        outer_csvfile=None,
        inner_csvfile=None,
        no_ptc=None,
        outer_dvclose=0.001,
        outer_maximum=150,
        under_relaxation=None,
        backtracking_number=0,
        backtracking_tolerance=0.0,
        backtracking_reduction_factor=0.0,
        backtracking_residual_limit=0.0,
        inner_maximum=100,
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
    imod5_data: dict,
    mf6_sim: Modflow6Simulation,
    times: list,
    unsa_svat_path: Path | str,
) -> imod.msw.MetaSwapModel:
    dis_pkg = mf6_sim["imported_model"]["dis"]
    msw_model = imod.msw.MetaSwapModel.from_imod5_data(imod5_data, dis_pkg, times)
    msw_model["oc"] = imod.msw.VariableOutputControl()
    msw_model.simulation_settings["unsa_svat_path"] = unsa_svat_path
    msw_model.simulation_settings["vegetation_mdl"] = (
        1  # Simple vegetation model instead of wofost
    )
    msw_model.simulation_settings["evapotranspiration_mdl"] = (
        1  # Simple evapotranspiration model
    )
    msw_model.simulation_settings["postmsw_opt"] = 0  # Turn off PostMetaSWAP output

    return msw_model


def import_lhm_mf6_and_msw(
    user_acceptance_dir: Path, user_acceptance_metaswap_dbase: Path
) -> tuple[Modflow6Simulation, imod.msw.MetaSwapModel]:
    """
    Convert iMOD5 LHM model to MODFLOW 6 using imod-python
    """
    lhm_dir = user_acceptance_dir / "LHM_transient"
    lhm_prjfile = lhm_dir / "model" / "LHM_transient_test.PRJ"
    logfile_path = lhm_dir / "logfile_mf6.txt"

    out_dir = lhm_dir / "mf6_imod-python"
    out_dir.mkdir(parents=True, exist_ok=True)

    # notes: M/D/Y and convert to list of datetime.
    # times = pd.date_range(start="1/1/2011", end="1/1/2012", freq="D").tolist()
    times = pd.date_range(start="1/1/2011", end="1/7/2011", freq="D").tolist()

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
        msw_model = convert_imod5_to_msw_model(
            imod5_data, mf6_simulation, times, user_acceptance_metaswap_dbase
        )

    return mf6_simulation, msw_model


def write_mete_grid_abspaths(user_acceptance_dir: Path) -> None:
    # Write mete_grid.inp with absolute paths
    path_msw_dir = user_acceptance_dir / "LHM_transient" / "model" / "DBASE" / "MSP"

    with open(path_msw_dir / "mete_grid_template.inp") as f:
        mete_grid_content = f.read()

    mete_grid_adapted = mete_grid_content.format(dir=path_msw_dir.resolve())

    with open(path_msw_dir / "mete_grid.inp", "w") as f:
        f.write(mete_grid_adapted)


@pytest.fixture(scope="session", autouse=False)
def lhm_coupling(
    user_acceptance_dir: Path, user_acceptance_metaswap_dbase: Path
) -> MetaMod:
    """
    Test coupling of LHM MODFLOW 6 and MetaSwap models
    """
    write_mete_grid_abspaths(user_acceptance_dir)
    mf6_simulation, msw_model = import_lhm_mf6_and_msw(
        user_acceptance_dir, user_acceptance_metaswap_dbase
    )

    driver_coupling = MetaModDriverCoupling(
        mf6_model="imported_model",
        mf6_recharge_package="msw-rch",
        mf6_wel_package="msw-sprinkling",
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


@pytest.fixture(scope="session", autouse=False)
def imod_path(
    written_lhm_conversion: Path,
):
    return {
        "idomain": written_lhm_conversion
        / "modflow6"
        / "imported_model"
        / "dis"
        / "idomain.bin",
        "dxc": written_lhm_conversion / "exchanges" / "nodenr2svat.dxc",
        "area_svat": written_lhm_conversion / "metaswap" / "area_svat.inp",
    }


@pytest.fixture(scope="session", autouse=False)
def imod5_path():
    user_acceptance_dir = Path(os.environ["USER_ACCEPTANCE_DIR"])
    lhm_dir = user_acceptance_dir / "LHM_transient"
    imod5_dir = lhm_dir / "reference_imod5_data"

    return {
        "idomain": imod5_dir / "IDOMAIN_L1.IDF",
        "dxc": imod5_dir / "NODENR2SVAT.DXC",
        "area_svat": imod5_dir / "AREA_SVAT.INP",
    }


@pytest.mark.user_acceptance
def test_lhm_metamod(
    lhm_coupling: MetaMod,
):
    """
    Test if the lhm_driver_coupling fixture works
    """
    assert isinstance(lhm_coupling, MetaMod)
    driver_coupling = lhm_coupling.coupling_list[0]
    mf6_simulation = lhm_coupling.mf6_simulation
    gwf_model = mf6_simulation[driver_coupling.mf6_model]
    msw_model = lhm_coupling.msw_model

    assert isinstance(driver_coupling, MetaModDriverCoupling)
    assert driver_coupling._check_sprinkling(msw_model, gwf_model)

    grid_mapping, rch_mapping, well_mapping = driver_coupling.derive_mapping(
        msw_model=msw_model,
        gwf_model=gwf_model,
    )

    assert grid_mapping.dataset["svat"].shape == (2, 1300, 1200)
    assert grid_mapping.dataset["mod_id"].shape == (2, 1300, 1200)
    assert rch_mapping.dataset["svat"].shape == (2, 1300, 1200)
    assert rch_mapping.dataset["rch_id"].shape == (2, 1300, 1200)
    # Check if well mappings are 1d arrays
    assert len(well_mapping.dataset["wel_id"].shape) == 1
    assert len(well_mapping.dataset["svat"].shape) == 1


@pytest.mark.user_acceptance
def test_lhm_written_dxc_files(
    written_lhm_conversion: Path,
) -> None:
    """
    Test if written dxc files are as expected
    """
    dxc_paths = list((written_lhm_conversion / "exchanges").glob("*.dxc"))
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

    settings = {"delimiter": "\s+", "index_col": False}
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
    assert len(list((written_lhm_conversion / "MetaSWAP").glob("*/*.idf"))) > 0

    # Test if Modflow6 output written
    headfile = (
        written_lhm_conversion / "Modflow6" / "imported_model" / "imported_model.hds"
    )
    cbcfile = (
        written_lhm_conversion / "Modflow6" / "imported_model" / "imported_model.cbc"
    )

    assert headfile.exists()
    assert cbcfile.exists()
    # If computation failed, Modflow6 usually writes a headfile and cbcfile of 0
    # bytes.
    assert headfile.stat().st_size > 0
    assert cbcfile.stat().st_size > 0


@pytest.mark.user_acceptance
def test_dxc_imod5_comparison(
    imod_path: dict,
    imod5_path: dict,
) -> None:
    """
    Compare written nodenr2svat dxc files to reference iMOD5 nodenr2svat dxc
    files. These should be nearly identical, the only differences should be
    caused by the following things:

    - Differences in idomain definition between iMOD5 and imod-python conversion
      to MODFLOW 6
    - iMOD5 couples some extra cells to deeper layers, which we do not couple in
      the imod-python conversion.
    """
    # Read dis grids
    shape = (15, 1300, 1200)
    max_rows = np.prod(shape)
    idomain = read_external_binaryfile(
        imod_path["idomain"], np.int32, max_rows
    ).reshape(shape)[0]
    idomain_imod5 = (
        imod.idf.open(imod5_path["idomain"]).sel(layer=1, drop=True).to_numpy()
    )

    # Read dxc files
    settings = {"delimiter": "\s+", "index_col": False}
    columns = ["node", "svat", "layer"]
    # Correct to zero-based indexing
    node2svat = pd.read_csv(imod_path["dxc"], names=columns, **settings) - 1
    node2svat_imod5 = pd.read_csv(imod5_path["dxc"], names=columns, **settings) - 1

    coupled_nodes, _ = coupled_nodes_grid(idomain, node2svat)
    coupled_nodes_imod5, _ = coupled_nodes_grid(idomain_imod5, node2svat_imod5)

    # Differences due to coupling in 166 cells
    diff_coupled = coupled_nodes_imod5 - coupled_nodes
    # Differences due to idomain in 204 cells
    is_active = idomain >= 1
    is_active_imod5 = idomain_imod5 >= 1
    diff_idomain = is_active_imod5.astype(np.int32) - is_active.astype(np.int32)
    # Filter differences in idomain from coupled differences:
    diff_filtered = np.where(diff_idomain ^ diff_coupled, diff_coupled, 0)
    # Assert no differences anymore
    assert np.all(diff_filtered == 0)


@pytest.mark.user_acceptance
def test_compare_coupled_metaswap_grids(
    imod_path: dict,
    imod5_path: dict,
) -> None:
    """
    Based on node2svat, reconstruct metaswap grid for soil physical unit and
    compare with those constructed with imod5 reference data.

    - Differences in idomain definition between iMOD5 and imod-python conversion
      to MODFLOW 6
    - iMOD5 couples some extra cells to deeper layers, which we do not couple in
      the imod-python conversion.
    """

    shape = (15, 1300, 1200)
    max_rows = np.prod(shape)
    idomain = read_external_binaryfile(
        imod_path["idomain"], np.int32, max_rows
    ).reshape(shape)[0]
    idomain_imod5 = (
        imod.idf.open(imod5_path["idomain"]).sel(layer=1, drop=True).to_numpy()
    )

    settings = {"delimiter": "\s+", "index_col": False}
    columns = ["node", "svat", "layer"]
    # Correct to zero-based indexing
    node2svat = pd.read_csv(imod_path["dxc"], names=columns, **settings) - 1
    node2svat_imod5 = pd.read_csv(imod5_path["dxc"], names=columns, **settings) - 1

    _, node2svat_coupled = coupled_nodes_grid(idomain, node2svat)
    node2svat_coupled[["svat"]] += 1  # back to 1-based indexing

    _, node2svat_coupled_imod5 = coupled_nodes_grid(idomain_imod5, node2svat_imod5)
    node2svat_coupled_imod5[["svat"]] += 1  # back to 1-based indexing

    is_active = idomain >= 1
    is_active_imod5 = idomain_imod5 >= 1

    area_svat = read_area_svat(imod_path["area_svat"])
    area_svat_imod5 = read_area_svat(imod5_path["area_svat"])

    node2area_svat = node2svat_coupled.join(area_svat.set_index("svat"), on="svat")
    node2area_svat_imod5 = node2svat_coupled_imod5.join(
        area_svat_imod5.set_index("svat"), on="svat"
    )

    varname = "soil_physical_unit"
    coupled_svats = np.zeros_like(is_active, dtype=np.int32)
    coupled_svats[node2area_svat["row"], node2area_svat["col"]] = node2area_svat[
        varname
    ]
    coupled_svats_imod5 = np.zeros_like(is_active, dtype=np.int32)
    coupled_svats_imod5[node2area_svat_imod5["row"], node2area_svat_imod5["col"]] = (
        node2area_svat_imod5[varname]
    )

    # There are differences in some cells where iMOD5 has inactive cells and iMOD
    # Python has not. Correct for that first, and the potential differences due to
    # idomain differences.
    coupled_svats_imod5 = np.where(is_active, coupled_svats_imod5, 0)
    coupled_svats = np.where(is_active_imod5, coupled_svats, 0)

    diff_soil_physical_unit = coupled_svats_imod5 - coupled_svats

    assert np.all(diff_soil_physical_unit == 0)
