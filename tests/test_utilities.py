from pathlib import Path
from typing import Dict, Tuple

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


def compute_tolerance_per_column_csvfiles(
    file1: Path,
    file2: Path,
    sep: str,
) -> Tuple[Dict[str, np.float], Dict[str, np.float]]:
    df1 = pd.read_csv(
        file1,
        sep,
    )
    df2 = pd.read_csv(
        file2,
        sep,
    )
    if df1.shape != df2.shape:
        raise ValueError(
            f"the dataframes in {file1} and {file2} do not have the same shape"
        )

    return compute_tolerance_per_column_dataframe(df1, df2)


def compute_tolerance_per_column_dataframe(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
) -> Tuple[Dict[str, np.float], Dict[str, np.float]]:
    if df1.shape != df2.shape:
        raise ValueError(f"the dataframes  do not have the same shape")

    col_titles = df1.columns

    abstol_dict = {}
    reltol_dict = {}
    for icol in col_titles:
        colname = icol
        col_df1 = pd.to_numeric(df1[icol], errors="coerce")
        col_df1_list = col_df1.to_list()
        col_df2 = pd.to_numeric(df2[icol], errors="coerce")
        col_df2_list = col_df2.to_list()

        maxtol = 0
        maxreltol = 0

        for irow in range(len(col_df1_list)):
            number_df1 = col_df1_list[irow]
            number_df2 = col_df2_list[irow]

            both_notnan = not np.isnan(number_df1) and not np.isnan(number_df2)
            both_nan = np.isnan(number_df1) and np.isnan(number_df2)
            if both_notnan and number_df1 != number_df2:
                maxtol = max(maxtol, abs(number_df1 - number_df2))
                maxreltol = max(
                    maxreltol,
                    abs(number_df1 - number_df2) / abs(0.5 * (number_df1 + number_df2)),
                )
            if not both_nan and not both_notnan:
                maxtol = np.nan
                maxreltol = np.nan
            abstol_dict[colname] = maxtol
            reltol_dict[colname] = maxreltol
    return (abstol_dict, reltol_dict)
