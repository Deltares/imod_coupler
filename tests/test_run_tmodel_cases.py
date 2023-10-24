from pathlib import Path
from typing import Dict, Set, Tuple

import numpy as np

eps = np.finfo(np.float_).eps
default_tolerance_balance: Dict[str, Tuple[float, float]] = {
    "default": (float(2 * eps), float(2 * eps)),
    "msw_decSpdmac_in": (58.39, 0.44),
    "msw_decSpdmic_in": (13.50, 2.0),
    "msw_Psgw_in": (750.0, 2.0),
    "msw_Pssw_in": (750.0, 2.0),
    "msw_qmodf_in": (9.59, 0.52),
    "msw_decS_in": (48.83, 1.74),
    "msw_sum_in": (59.86, 0.0088),
    "msw_Epd_out": (5.577, 2.0),
    "msw_Ebs_out": (5.58, 0.0093),
    "msw_Tact_out": (0.68, 0.00040),
    "msw_decS_out": (35.37, 0.33),
    "msw_sum_out": (35.37, 0.027),
    "mf_STO-SS_IN": (139.95, 0.147),
    "mf_RIV_IN": (24.17, 0.040),
    "mf_WEL_IN": (24.17, 0.041),
    "mf_RCH_IN": (47.49, 0.67),
    "mf_STO-SS_OUT": (32.35, 2.0),
    "mf_DRN_OUT": (0.06, 0.00018),
    "mf_RIV_OUT": (28.79, 0.015),
    "mf_WEL_OUT": (28.83, 0.02),
    "mf_RCH_OUT": (111.971, 2.0),
}


def case_tmodel_d_no_sprinkling(
    test_data_folder: Path,
) -> Tuple[Path, Set[str], str, str, Dict[str, Tuple[float, float]]]:
    tmodel_input_folder = test_data_folder / "t_model"

    files_to_skip = {
        "mf6_msw_sprinkling_map",
        "mf6_msw_well_pkg",
    }

    mf6_model_rootname = "T-MODEL-D.LST"

    csv_reference_file = "waterbalance_tmodel_d_no_sprinkling.csv"

    tolerance_balance = default_tolerance_balance

    return (
        tmodel_input_folder,
        files_to_skip,
        mf6_model_rootname,
        csv_reference_file,
        tolerance_balance,
    )


def case_tmodel_f_no_sprinkling(
    test_data_folder: Path,
) -> Tuple[Path, Set[str], str, str, Dict[str, Tuple[float, float]]]:
    tmodel_input_folder = test_data_folder / "t_model_f"
    files_to_skip = {
        "mf6_msw_sprinkling_map",
        "mf6_msw_well_pkg",
    }
    mf6_model_rootname = "T-MODEL-F.LST"

    csv_reference_file = "waterbalance_tmodel_f_no_sprinkling.csv"
    tolerance_balance = default_tolerance_balance

    return (
        tmodel_input_folder,
        files_to_skip,
        mf6_model_rootname,
        csv_reference_file,
        tolerance_balance,
    )


def case_tmodel_f_without_dflow(
    test_data_folder: Path,
) -> Tuple[Path, Set[str], str, str, Dict[str, Tuple[float, float]]]:
    tmodel_input_folder = test_data_folder / "t_model_f"
    files_to_skip = {
        "msw_ponding_to_dfm_2d_dv_dmm",
        "dfm_2d_waterlevels_to_msw_h_dmm",
        "mf6_river2_to_dfm_1d_q_dmm",
        "mf6_drainage_to_dfm_1d_q_dmm",
        "msw_sprinkling_to_dfm_1d_q_dmm",
        "msw_runoff_to_dfm_1d_q_dmm",
        "mf6_river_to_dfm_1d_q_dmm",
        "dfm_1d_waterlevel_to_mf6_river_stage_dmm",
        "mf6_msw_sprinkling_map",
        "mf6_msw_well_pkg",
    }
    mf6_model_rootname = "T-MODEL-F.LST"

    csv_reference_file = "waterbalance_tmodel_f_without_dflow.csv"
    tolerance_balance = default_tolerance_balance

    return (
        tmodel_input_folder,
        files_to_skip,
        mf6_model_rootname,
        csv_reference_file,
        tolerance_balance,
    )
