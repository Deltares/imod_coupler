from pathlib import Path

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


def numeric_csvfiles_equal(
    file1: Path,
    file2: Path,
    sep: str = ";",
    abstol: float = 1e100,
    reltol: float = 1e100,
) -> bool:
    df1 = pd.read_csv(
        file1,
        sep,
    )
    df2 = pd.read_csv(
        file2,
        sep,
    )
    if df1.shape != df2.shape:
        print(f"the dataframes in {file1} and {file2} do not have the same shape")
        return False
    return numeric_dataframes_equal(df1, df2, abstol, reltol)


def numeric_dataframes_equal(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    abstol: float = 1e100,
    reltol: float = 1e100,
) -> bool:
    if df1.shape != df2.shape:
        print(f"the dataframes  do not have the same shape")
        return False

    col_titles = df1.columns

    for icol in col_titles:
        col_df1 = pd.to_numeric(df1[icol], errors="coerce")
        col_df1_list = col_df1.to_list()
        col_df2 = pd.to_numeric(df2[icol], errors="coerce")
        col_df2_list = col_df2.to_list()

        for irow in range(len(col_df1_list)):
            number_df1 = col_df1_list[irow]
            number_df2 = col_df2_list[irow]

            both_notnan = not np.isnan(number_df1) and not np.isnan(number_df2)
            both_nan = np.isnan(number_df1) and np.isnan(number_df2)
            abstol_succeeded = abs(number_df1 - number_df2) < abstol
            reltol_succeeded = (
                abs(number_df1 - number_df2)
                <= abs(0.5 * (number_df1 + number_df2)) * reltol
            )

            if both_nan or (both_notnan and (abstol_succeeded or reltol_succeeded)):
                continue
            else:
                print(f"difference on col {icol} and row {irow}")
                return False
    return True
