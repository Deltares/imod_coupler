import textwrap
from pathlib import Path

from hydrolib.core.dflowfm.mdu.models import FMModel
from imod.mf6 import Modflow6Simulation
from imod.msw import MetaSwapModel

from imod_coupler.drivers.dfm_metamod.dfm_metamod_model import DfmMetaModModel


def test_write_toml_file(
    mf6_model_with_river: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
    prepared_dflowfm_model: FMModel,
    tmp_path_dev: Path,
) -> None:
    model = DfmMetaModModel(
        prepared_msw_model,
        mf6_model_with_river,
        prepared_dflowfm_model,
        "rch_msw",  # mf6_msw_recharge_pkg
        "RIV_SYS1",  # mf6_river_active_pkg
        "RIV_SYS2",  # mf6_river_passive_pkg
        "DRN_SYS1",  # mf6_drain_pkg
        "wells_msw",  # mf6_wel_correction_pkg
        Path("mf6_river_to_dfm_1d_q_dmm_path"),
        Path("dfm_1d_waterlevel_to_mf6_river_stage_dmm_path"),
        Path("mf6_river2_to_dfm_1d_q_dmm_path"),
        Path("mf6_drainage_to_dfm_1d_q_dmm_path"),
        Path("msw_runoff_to_dfm_1d_q_dmm_path"),
        Path("msw_sprinkling_to_dfm_1d_q_dmm_path"),
        Path("msw_ponding_to_dfm_2d_dv_dmm_path"),
        Path("dfm_2d_waterlevels_to_msw_h_dmm_path"),
        Path(
            "dfm_1d_points_dat_path",
        ),
        Path("output_config_file"),
    )

    model.write(tmp_path_dev, "mf6.dll", "msw.dll", "msw_dep.dll", "dflow.dll")

    expected = textwrap.dedent(
        """\
    timing = false
    log_level = "INFO"
    driver_type = "dfm_metamod"

    [driver.kernels.modflow6]
    dll = "mf6.dll"
    work_dir = ".\Modflow6"

    [driver.kernels.metaswap]
    dll = "msw.dll"
    work_dir = ".\MetaSWAP"
    dll_dep_dir = "msw_dep.dll"

    [driver.kernels.dflowfm]
    dll = "dflow.dll"
    work_dir = ".\dflow-fm"

    [[driver.coupling]]
    dfm_model = "dfm.mdu"
    mf6_model = "GWF_1"
    mf6_msw_node_map = "./exchanges/nodenr2svat.dxc"
    mf6_msw_recharge_pkg = "rch_msw"
    mf6_river_active_pkg = "RIV_SYS1"
    mf6_river_passive_pkg = "RIV_SYS2"
    mf6_wel_correction_pkgkey = "DRN_SYS1"
    mf6_msw_recharge_map = "./exchanges/rchindex2svat.dxc"
    mf6_msw_well_pkg = "wells_msw"
    mf6_msw_sprinkling_map = "./exchanges/wellindex2svat.dxc"
    mf6_river_to_dfm_1d_q_dmm = "mf6_river_to_dfm_1d_q_dmm_path"
    dfm_1d_waterlevel_to_mf6_river_stage_dmm = "dfm_1d_waterlevel_to_mf6_river_stage_dmm_path"
    mf6_river2_to_dfm_1d_q_dmm = "mf6_river2_to_dfm_1d_q_dmm_path"
    mf6_drainage_to_dfm_1d_q_dmm = "mf6_drainage_to_dfm_1d_q_dmm_path"
    msw_runoff_to_dfm_1d_q_dmm = "msw_runoff_to_dfm_1d_q_dmm_path"
    msw_sprinkling_to_dfm_1d_q_dmm = "msw_sprinkling_to_dfm_1d_q_dmm_path"
    msw_ponding_to_dfm_2d_dv_dmm = "msw_ponding_to_dfm_2d_dv_dmm_path"
    dfm_2d_waterlevels_to_msw_h_dmm = "dfm_2d_waterlevels_to_msw_h_dmm_path"
    dfm_1d_points_dat = "dfm_1d_points_dat_path"
    output_config_file = "output_config_file"
    """
    )

    filename = str(tmp_path_dev) + "\\" + "imod_coupler.toml"
    with open(filename, "r+") as f:
        actual = f.read()
    assert actual.replace("\\\\", "\\") == expected
