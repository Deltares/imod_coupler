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


def case_tmodel_a(
    test_data_folder: Path,
) -> Tuple[Path, Set[str], str, str, Dict[str, Tuple[float, float]]]:
    tmodel_input_folder = test_data_folder / "t_model" / "t_model_A"

    files_to_skip = {}
    mf6_model_rootname = "T-MODEL-D.LST"
    csv_reference_file = "waterbalance_tmodel_a.csv"
    tolerance_balance = default_tolerance_balance

    return (
        tmodel_input_folder,
        mf6_model_rootname,
        csv_reference_file,
        tolerance_balance,
    )

def case_tmodel_a(
    test_data_folder: Path,
) -> Tuple[Path, Set[str], str, str, Dict[str, Tuple[float, float]]]:
    tmodel_input_folder = test_data_folder / "t_model" / "t_model_A"

    files_to_skip = {}
    mf6_model_rootname = "T-MODEL-D.LST"
    csv_reference_file = "waterbalance_tmodel_a.csv"
    tolerance_balance = default_tolerance_balance

    return (
        tmodel_input_folder,
        mf6_model_rootname,
        csv_reference_file,
        tolerance_balance,
    )

def case_tmodel_a(
    test_data_folder: Path,
) -> Tuple[Path, Set[str], str, str, Dict[str, Tuple[float, float]]]:
    tmodel_input_folder = test_data_folder / "t_model" / "t_model_A"

    files_to_skip = {}
    mf6_model_rootname = "T-MODEL-D.LST"
    csv_reference_file = "waterbalance_tmodel_a.csv"
    tolerance_balance = default_tolerance_balance

    return (
        tmodel_input_folder,
        mf6_model_rootname,
        csv_reference_file,
        tolerance_balance,
    )

def case_tmodel_a(
    test_data_folder: Path,
) -> Tuple[Path, Set[str], str, str, Dict[str, Tuple[float, float]]]:
    tmodel_input_folder = test_data_folder / "t_model" / "t_model_A"

    files_to_skip = {}
    mf6_model_rootname = "T-MODEL-A.LST"
    csv_reference_file = "waterbalance_tmodel_a.csv"
    tolerance_balance = default_tolerance_balance

    return (
        tmodel_input_folder,
        mf6_model_rootname,
        csv_reference_file,
        tolerance_balance,
    )

def case_tmodel_b(
    test_data_folder: Path,
) -> Tuple[Path, Set[str], str, str, Dict[str, Tuple[float, float]]]:
    tmodel_input_folder = test_data_folder / "t_model" / "t_model_B"

    files_to_skip = {}
    mf6_model_rootname = "T-MODEL-B.LST"
    csv_reference_file = "waterbalance_tmodel_b.csv"
    tolerance_balance = default_tolerance_balance

    return (
        tmodel_input_folder,
        mf6_model_rootname,
        csv_reference_file,
        tolerance_balance,
    )

def case_tmodel_c(
    test_data_folder: Path,
) -> Tuple[Path, Set[str], str, str, Dict[str, Tuple[float, float]]]:
    tmodel_input_folder = test_data_folder / "t_model" / "t_model_C"

    files_to_skip = {}
    mf6_model_rootname = "T-MODEL-C.LST"
    csv_reference_file = "waterbalance_tmodel_c.csv"
    tolerance_balance = default_tolerance_balance

    return (
        tmodel_input_folder,
        mf6_model_rootname,
        csv_reference_file,
        tolerance_balance,
    )

def case_tmodel_d(
    test_data_folder: Path,
) -> Tuple[Path, Set[str], str, str, Dict[str, Tuple[float, float]]]:
    tmodel_input_folder = test_data_folder / "t_model" / "t_model_D"

    files_to_skip = {}
    mf6_model_rootname = "T-MODEL-D.LST"
    csv_reference_file = "waterbalance_tmodel_d.csv"
    tolerance_balance = default_tolerance_balance

    return (
        tmodel_input_folder,
        mf6_model_rootname,
        csv_reference_file,
        tolerance_balance,
    )

def case_tmodel_e(
    test_data_folder: Path,
) -> Tuple[Path, Set[str], str, str, Dict[str, Tuple[float, float]]]:
    tmodel_input_folder = test_data_folder / "t_model" / "t_model_E"

    files_to_skip = {}
    mf6_model_rootname = "T-MODEL-E.LST"
    csv_reference_file = "waterbalance_tmodel_e.csv"
    tolerance_balance = default_tolerance_balance

    return (
        tmodel_input_folder,
        mf6_model_rootname,
        csv_reference_file,
        tolerance_balance,
    )

def case_tmodel_e(
    test_data_folder: Path,
) -> Tuple[Path, Set[str], str, str, Dict[str, Tuple[float, float]]]:
    tmodel_input_folder = test_data_folder / "t_model" / "t_model_E"

    files_to_skip = {}
    mf6_model_rootname = "T-MODEL-E.LST"
    csv_reference_file = "waterbalance_tmodel_e.csv"
    tolerance_balance = default_tolerance_balance

    return (
        tmodel_input_folder,
        mf6_model_rootname,
        csv_reference_file,
        tolerance_balance,
    )

def case_tmodel_f(
    test_data_folder: Path,
) -> Tuple[Path, Set[str], str, str, Dict[str, Tuple[float, float]]]:
    tmodel_input_folder = test_data_folder / "t_model" / "t_model_F"

    files_to_skip = {}
    mf6_model_rootname = "T-MODEL-F.LST"
    csv_reference_file = "waterbalance_tmodel_f.csv"
    tolerance_balance = default_tolerance_balance

    return (
        tmodel_input_folder,
        mf6_model_rootname,
        csv_reference_file,
        tolerance_balance,
    )

def case_tmodel_g(
    test_data_folder: Path,
) -> Tuple[Path, Set[str], str, str, Dict[str, Tuple[float, float]]]:
    tmodel_input_folder = test_data_folder / "t_model" / "t_model_G"

    files_to_skip = {}
    mf6_model_rootname = "T-MODEL-G.LST"
    csv_reference_file = "waterbalance_tmodel_g.csv"
    tolerance_balance = default_tolerance_balance

    return (
        tmodel_input_folder,
        mf6_model_rootname,
        csv_reference_file,
        tolerance_balance,
    )

