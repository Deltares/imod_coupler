from pathlib import Path

import numpy as np
import pandas as pd
import csv

from imod.mf6 import Modflow6Simulation
from imod.mf6.model_gwf import GroundwaterFlowModel


def diff_per_column_dataframe(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    tolerance: dict[str, tuple[float, float]],
) -> tuple[dict[str, list[int]], dict[str, list[int]], dict[str, tuple[bool, bool]]]:
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
    tolerance: dict[str, tuple[float, float]],
) -> bool:
    df1 = pd.read_csv(
        file1,
        sep=sep,
    )
    df2 = pd.read_csv(
        file2,
        sep=sep,
    )
    if df1.shape[0] != df2.shape[0]:
        print(f"the dataframes in {file1} and {file2} differ in length")
        return False

    # rownumbers with significant difference per variable
    _, _, failed = diff_per_column_dataframe(df1, df2, tolerance)
    # is there any significant difference whatsoever?
    columns_with_differences = [v[0] for v in failed.items() if v[1] != (False, False)]
    is_different = any(columns_with_differences)

    # print column name with differences
    if is_different:
        print("columns with differences:")
        print(columns_with_differences)

    return not is_different


def write_mete_grid_inp_abs_path(meteo_output_dir: Path, mete_grid: Path):
    # WORKAROUND: set absolute paths in file mete_grid.inp
    df = pd.read_csv(mete_grid, header=None)
    for row in range(df.shape[0]):
        df.loc[row, 2] = str(meteo_output_dir / Path(df.loc[row, 2]))
        df.loc[row, 3] = str(meteo_output_dir / Path(df.loc[row, 3]))
    for col in [2, 3, 4, 5, 6]:
        df.loc[:, col] = '"' + df[col] + '"'
    df.to_csv(
        mete_grid,
        header=False,
        quoting=csv.QUOTE_NONE,
        float_format="%.4f",
        index=False,
    )


def get_mf6_gwf_model_names(mf6_splitted: Modflow6Simulation) -> list[str]:
    mf6_model_name_list = [
        model_name
        for model_name, model in mf6_splitted.items()
        if isinstance(model, GroundwaterFlowModel)
    ]
    return mf6_model_name_list
