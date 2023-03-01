import shutil
from pathlib import Path

import tomli
import tomli_w
from test_scripts.water_balance.combine import create_waterbalance_file
from test_utilities import compute_tolerance_per_column_csvfiles, fill_para_sim_template

from imod_coupler.__main__ import run_coupler

tmodel_absolute_tolerance = {
    "t": 0,
    "fm_bndin": 0,
    "fm_prec": 0,
    "fm_qin1d": 0,
    "fm_qin2d": 0,
    "fm_latin1d": 0,
    "fm_bndout": 0,
    "fm_evap": 0,
    "fm_qout1d": 0,
    "fm_qout2d": 0,
    "fm_latout1d": 0,
    "fm_stoin": 0,
    "fm_stoout": 0,
    "fm_totalin": 0,
    "fm_totalout": 0,
    "fm_totalin+out": 0,
    "msw_decSic_in": 0,
    "msw_decSpdmac_in": 58.39200000000005,
    "msw_decSpdmic_in": 13.504000000000019,
    "msw_Pm_in": 0,
    "msw_Psgw_in": 750.0,
    "msw_Pssw_in": 750.0,
    "msw_qrun_in": 0,
    "msw_qdr_in": 0,
    "msw_qmodf_in": 9.587000000000002,
    "msw_decS_in": 48.83400000000029,
    "msw_sum_in": 59.85699999999997,
    "msw_decSic_out": 0,
    "msw_decSpdmac_out": 0,
    "msw_decSpdmic_out": 0,
    "msw_Esp_out": 0,
    "msw_Eic_out": 0,
    "msw_Epd_out": 5.577,
    "msw_Ebs_out": 5.576999999999998,
    "msw_Tact_out": 0.6839999999999691,
    "msw_qrun_out": 0,
    "msw_qdr_out": 0,
    "msw_qspgw_out": 0,
    "msw_qmodf_out": 0,
    "msw_decS_out": 35.36900000000003,
    "msw_sum_out": 35.368999999999915,
    "mf_STO_IN": 0,
    "mf_STO-SS_IN": 139.9469999999999,
    "mf_CHD_IN": 0,
    "mf_DRN_IN": 0,
    "mf_RIV_IN": 24.171999999999912,
    "mf_WEL_IN": 24.171999999999912,
    "mf_DXC_IN": 0,
    "mf_RCH_IN": 47.4940000000006,
    "mf_STO_OUT": 0,
    "mf_STO-SS_OUT": 32.35199999999986,
    "mf_CHD_OUT": 0,
    "mf_DRN_OUT": 0.05899999999996908,
    "mf_RIV_OUT": 28.791000000000167,
    "mf_WEL_OUT": 28.826999999999998,
    "mf_DXC_OUT": 0,
    "mf_RCH_OUT": 111.971,
}

tmodel_relative_tolerance = {
    "t": 0,
    "fm_bndin": 0,
    "fm_prec": 0,
    "fm_qin1d": 0,
    "fm_qin2d": 0,
    "fm_latin1d": 0,
    "fm_bndout": 0,
    "fm_evap": 0,
    "fm_qout1d": 0,
    "fm_qout2d": 0,
    "fm_latout1d": 0,
    "fm_stoin": 0,
    "fm_stoout": 0,
    "fm_totalin": 0,
    "fm_totalout": 0,
    "fm_totalin+out": 0,
    "msw_decSic_in": 0,
    "msw_decSpdmac_in": 0.43921823047603603,
    "msw_decSpdmic_in": 2.0,
    "msw_Pm_in": 0,
    "msw_Psgw_in": 2.0,
    "msw_Pssw_in": 2.0,
    "msw_qrun_in": 0,
    "msw_qdr_in": 0,
    "msw_qmodf_in": 0.5187630204810477,
    "msw_decS_in": 1.738804415746719,
    "msw_sum_in": 0.008832916482180724,
    "msw_decSic_out": 0,
    "msw_decSpdmac_out": 0,
    "msw_decSpdmic_out": 0,
    "msw_Esp_out": 0,
    "msw_Eic_out": 0,
    "msw_Epd_out": 2.0,
    "msw_Ebs_out": 0.009302325581395331,
    "msw_Tact_out": 0.00040004085009287023,
    "msw_qrun_out": 0,
    "msw_qdr_out": 0,
    "msw_qspgw_out": 0,
    "msw_qmodf_out": 0,
    "msw_decS_out": 0.32987855280727424,
    "msw_sum_out": 0.026843431892503242,
    "mf_STO_IN": 0,
    "mf_STO-SS_IN": 0.14698953385084776,
    "mf_CHD_IN": 0,
    "mf_DRN_IN": 0,
    "mf_RIV_IN": 0.04059259955867372,
    "mf_WEL_IN": 0.04059259955867372,
    "mf_DXC_IN": 0,
    "mf_RCH_IN": 0.6666666666666666,
    "mf_STO_OUT": 0,
    "mf_STO-SS_OUT": 2.0,
    "mf_CHD_OUT": 0,
    "mf_DRN_OUT": 0.00017917038040291797,
    "mf_RIV_OUT": 0.012186885901651212,
    "mf_WEL_OUT": 0.01988161142022716,
    "mf_DXC_OUT": 0,
    "mf_RCH_OUT": 2.0,
}


def test_run_tmodel_devel(
    tmp_path_dev: Path,
    tmodel_input_folder: Path,
    modflow_dll_devel: Path,
    dflowfm_dll: Path,
    metaswap_dll_devel: Path,
    metaswap_dll_dep_dir_devel: Path,
    metaswap_lookup_table: Path,
    reference_result_folder: Path,
) -> None:
    shutil.copytree(tmodel_input_folder, tmp_path_dev)

    toml_file_path = tmp_path_dev / "imod_coupler.toml"
    toml_dict = {}
    with open(toml_file_path, "rb") as f:
        toml_dict = tomli.load(f)

    toml_dict["driver"]["kernels"]["modflow6"]["dll"] = str(modflow_dll_devel)
    toml_dict["driver"]["kernels"]["dflowfm"]["dll"] = str(dflowfm_dll)
    toml_dict["driver"]["kernels"]["metaswap"]["dll"] = str(metaswap_dll_devel)
    toml_dict["driver"]["kernels"]["metaswap"]["dll_dep_dir"] = str(
        metaswap_dll_dep_dir_devel
    )
    with open(toml_file_path, "wb") as toml_file:
        tomli_w.dump(toml_dict, toml_file)

    fill_para_sim_template(tmp_path_dev / "MetaSWAP", metaswap_lookup_table)

    run_coupler(toml_file_path)

    waterbalance_result = run_waterbalance_script_on_tmodel(tmp_path_dev)

    csv_reference_file = (
        reference_result_folder / "test_run_tmodel" / "waterbalance.csv"
    )

    abstol, reltol = compute_tolerance_per_column_csvfiles(
        waterbalance_result, csv_reference_file, ";"
    )

    error = False
    columns = abstol.keys()
    for column in columns:
        if tmodel_absolute_tolerance[column] < abstol[column]:
            print(
                f"for column {column} the absolute difference {abstol[column]} exceeds the  maximum {tmodel_absolute_tolerance[column]} "
            )
            error = True
        if tmodel_relative_tolerance[column] < reltol[column]:
            print(
                f"for column {column} the relative difference {reltol[column]} exceeds the  maximum {tmodel_relative_tolerance[column]} "
            )
            error = True

    assert not error


def test_run_tmodel_regression(
    tmp_path_dev: Path,
    tmodel_input_folder: Path,
    modflow_dll_regression: Path,
    dflowfm_dll_regression: Path,
    metaswap_dll_regression: Path,
    metaswap_dll_dep_dir_regression: Path,
    metaswap_lookup_table: Path,
    reference_result_folder: Path,
) -> None:
    shutil.copytree(tmodel_input_folder, tmp_path_dev)

    toml_file_path = tmp_path_dev / "imod_coupler.toml"
    toml_dict = {}
    with open(toml_file_path, "rb") as f:
        toml_dict = tomli.load(f)

    toml_dict["driver"]["kernels"]["modflow6"]["dll"] = str(modflow_dll_regression)
    toml_dict["driver"]["kernels"]["dflowfm"]["dll"] = str(dflowfm_dll_regression)
    toml_dict["driver"]["kernels"]["metaswap"]["dll"] = str(metaswap_dll_regression)
    toml_dict["driver"]["kernels"]["metaswap"]["dll_dep_dir"] = str(
        metaswap_dll_dep_dir_regression
    )
    with open(toml_file_path, "wb") as toml_file:
        tomli_w.dump(toml_dict, toml_file)

    fill_para_sim_template(tmp_path_dev / "MetaSWAP", metaswap_lookup_table)

    run_coupler(toml_file_path)

    waterbalance_result = run_waterbalance_script_on_tmodel(tmp_path_dev)

    csv_reference_file = (
        reference_result_folder / "test_run_tmodel" / "waterbalance.csv"
    )
    abstol, reltol = compute_tolerance_per_column_csvfiles(
        waterbalance_result, csv_reference_file, ";"
    )

    error = False
    columns = abstol.keys()
    for column in columns:
        if tmodel_absolute_tolerance[column] < abstol[column]:
            print(
                f"for column {column} the absolute difference {abstol[column]} exceeds the  maximum {tmodel_absolute_tolerance[column]} "
            )
            error = True
        if tmodel_relative_tolerance[column] < reltol[column]:
            print(
                f"for column {column} the relative difference {reltol[column]} exceeds the  maximum {tmodel_relative_tolerance[column]} "
            )
            error = True

    assert not error


def run_waterbalance_script_on_tmodel(testdir: Path) -> Path:
    modflow_out_file = testdir / "Modflow6" / "GWF_1" / "T-MODEL-D.LST"
    dflow_out_file = testdir / "dflow-fm" / "DFM_OUTPUT_FlowFM" / "FlowFM_his.nc"
    metaswap_out_file = testdir / "MetaSWAP" / "msw" / "csv" / "tot_svat_dtgw.csv"

    csv_file = testdir / "water_balance.csv"
    create_waterbalance_file(
        dflow_out_file, metaswap_out_file, modflow_out_file, output_file_csv=csv_file
    )
    return csv_file
