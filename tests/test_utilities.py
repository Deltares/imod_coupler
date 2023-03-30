from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

eps = np.finfo(np.float_).eps
tolerance_balance: Dict[str, Tuple[float, float]] = {
    "default": (2 * eps, 2 * eps),
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


def fill_para_sim_template(msw_folder: Path, path_unsat_dbase: Path) -> None:
    """
    Fill para_sim.inp template in the folder with the path to the unsaturated
    zone database.
    """
    template_file = msw_folder / "para_sim_template.inp"
    if not template_file.exists():
        raise ValueError(f"could not find file {template_file}")
    with open(msw_folder / "para_sim_template.inp") as f:
        para_sim_text = f.read()

    para_sim_text = para_sim_text.replace("{{unsat_path}}", f"{path_unsat_dbase}\\")

    with open(msw_folder / "para_sim.inp", mode="w") as f:
        f.write(para_sim_text)


def diff_per_column_dataframe(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    tolerance: Dict[str, tuple[float, float]],
) -> tuple[Dict[str, list[int]], Dict[str, list[int]], Dict[str, tuple[bool, bool]]]:
    failed = {}
    absfailedndx = {}
    relfailedndx = {}
    for varname in list(df1)[1:]:
        if varname not in df2:
            failed[varname] = (True, True)
        s1 = df1[varname]
        s2 = df2[varname]
        if varname in tolerance:
            (abstol, reltol) = tolerance[varname]
        else:
            (abstol, reltol) = tolerance["default"]
        # only where both are nan
        nan_match = np.logical_and(s1.isna(), s2.isna())
        # where abolute matches, but the matching nans are excused
        abs_match = np.logical_or((abs(s2 - s1) <= abstol), nan_match)
        # where relative matches, but the matching nans are excused
        rel_match = np.logical_or((abs(s2 - s1) <= abs(s1 * reltol)), nan_match)
        absfailedndx[varname] = list(s2[~abs_match].index)
        relfailedndx[varname] = list(s2[~rel_match].index)
        failed[varname] = (
            len(absfailedndx[varname]) > 0,
            len(relfailedndx[varname]) > 0,
        )
    return absfailedndx, relfailedndx, failed


def numeric_csvfiles_equal(
    file1: Path,
    file2: Path,
    sep: str,
    tolerance: Dict[str, tuple[float, float]],
) -> bool:
    df1 = pd.read_csv(
        file1,
        sep,
    )
    df2 = pd.read_csv(
        file2,
        sep,
    )
    if df1.shape[0] != df2.shape[0]:
        print(f"the dataframes in {file1} and {file2} differ in length")
        return False

    # rownumbers with significant difference per variable
    absfailedndx, relfailedndx, failed = diff_per_column_dataframe(df1, df2, tolerance)
    # is there any significant difference whatsoever?
    isDifferent = any([v != (False, False) for v in failed.values()])

    return not isDifferent


def numeric_dataframes_equal(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    abstol: float,
    reltol: float,
    tol: Optional[Dict[str, tuple[np.float_, np.float_]]] = None,
) -> bool:
    if tol is None:
        tol = {}
    tol["default"] = (abstol, reltol)
    absfailedndx, relfailedndx, failed = diff_per_column_dataframe(df1, df2, tol)
    any_failure = any([any(ff) for ff in failed.values()])
    return not any_failure
