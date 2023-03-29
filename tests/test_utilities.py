from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd


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
    tolerance: Dict[str, tuple[np.float_, np.float_]],
) -> tuple[Dict[str, list[int]], Dict[str, list[int]], Dict[str, tuple[bool, bool]]]:
    failed = {}
    absfailedndx = {}
    relfailedndx = {}
    for varname in list(df1):
        if varname not in df2:
            failed[varname] = (True, True)
        s1 = df1[varname]
        s2 = df2[varname]
        if varname in tolerance:
            tol = tolerance[varname]
        else:
            tol = tolerance["default"]
        # only where both are nan
        nan_match = np.logical_and(np.isnan(s1), np.isnan(s2))
        # where abolute matches, but the matching nans are excused
        abs_match = np.logical_or((abs(s2 - s1) <= tol[0]), nan_match)
        # where relative matches, but the matching nans are excused
        rel_match = np.logical_or((abs(s2 - s1) <= abs(s1 * tol[1])), nan_match)
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
    tolerance: Dict[str, tuple[np.float_, np.float_]],
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
    isDifferent = any(failed.values())

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
