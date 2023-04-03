import os
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from test_utilities import diff_per_column_dataframe, numeric_csvfiles_equal

sep = ";"


def test_compare_absolute_fail(tmp_path_dev: Path):
    frame1 = pd.DataFrame([[10, -10], [1, -1]])
    frame2 = pd.DataFrame([[10.01, -10.01], [1.01, -1.01]])
    os.mkdir(tmp_path_dev)
    frame1.to_csv(tmp_path_dev / "frame1.csv", sep=sep)
    frame2.to_csv(tmp_path_dev / "frame2.csv", sep=sep)
    tol = {"default": (0.009, 100.0)}
    assert not numeric_csvfiles_equal(
        tmp_path_dev / "frame1.csv", tmp_path_dev / "frame2.csv", sep, tol
    )


def test_compare_absolute_succeed(tmp_path_dev: Path):
    frame1 = pd.DataFrame([[10, -10], [1, -1]])
    frame2 = pd.DataFrame([[10.01, -10.01], [1.01, -1.01]])
    os.mkdir(tmp_path_dev)
    frame1.to_csv(tmp_path_dev / "frame1.csv", sep=sep)
    frame2.to_csv(tmp_path_dev / "frame2.csv", sep=sep)
    tol = {"default": (0.011, 100.0)}
    assert numeric_csvfiles_equal(
        tmp_path_dev / "frame1.csv", tmp_path_dev / "frame2.csv", sep, tol
    )


def test_compare_relative_fail(tmp_path_dev: Path):
    frame1 = pd.DataFrame([[10, -10], [1, -1]])
    frame2 = pd.DataFrame([[10.01, -10.01], [1.01, -1.01]])
    os.mkdir(tmp_path_dev)
    frame1.to_csv(tmp_path_dev / "frame1.csv", sep=sep)
    frame2.to_csv(tmp_path_dev / "frame2.csv", sep=sep)
    tol = {"default": (100.0, 0.001)}
    assert not numeric_csvfiles_equal(
        tmp_path_dev / "frame1.csv", tmp_path_dev / "frame2.csv", sep, tol
    )


def test_compare_relative_succeed(tmp_path_dev: Path):
    frame1 = pd.DataFrame([[10, -10], [1, -1]])
    frame2 = pd.DataFrame([[10.01, -10.01], [1.01, -1.01]])
    os.mkdir(tmp_path_dev)
    frame1.to_csv(tmp_path_dev / "frame1.csv", sep=sep)
    frame2.to_csv(tmp_path_dev / "frame2.csv", sep=sep)
    tol = {"default": (100.0, 0.011)}
    assert numeric_csvfiles_equal(
        tmp_path_dev / "frame1.csv", tmp_path_dev / "frame2.csv", sep, tol
    )


def test_compare_with_nan(tmp_path_dev: Path):
    frame1 = pd.DataFrame([[np.nan, -10], [1, -1]])
    frame2 = pd.DataFrame([[np.nan, -10.01], [1.01, -1.01]])
    os.mkdir(tmp_path_dev)
    frame1.to_csv(tmp_path_dev / "frame1.csv", sep=sep)
    frame2.to_csv(tmp_path_dev / "frame2.csv", sep=sep)
    tol = {"default": (100.0, 0.011)}
    assert numeric_csvfiles_equal(
        tmp_path_dev / "frame1.csv", tmp_path_dev / "frame2.csv", sep, tol
    )


def test_compare_with_nan_fails(tmp_path_dev: Path):
    frame1 = pd.DataFrame([[np.nan, -10], [1, -1]])
    frame2 = pd.DataFrame([[10, np.nan], [1, -1]])
    os.mkdir(tmp_path_dev)
    frame1.to_csv(tmp_path_dev / "frame1.csv", sep=sep)
    frame2.to_csv(tmp_path_dev / "frame2.csv", sep=sep)
    tol = {"default": (100.0, 0.011)}
    assert not numeric_csvfiles_equal(
        tmp_path_dev / "frame1.csv", tmp_path_dev / "frame2.csv", sep, tol
    )


def test_compare_varying_tolerances():
    frame1 = pd.DataFrame()
    frame1["index"] = [0, 1, 2, 3, 4]
    frame1["Var A"] = [0.01, 0.013, -50.06, -0.04, 0.001]
    frame1["Var B"] = [0.01, 0.013, -50.06, -0.04, 0.001]
    frame1["Var C"] = [0.01, 0.013, -50.06, -0.04, 0.001]

    frame2 = pd.DataFrame()
    frame2["index"] = [0, 1, 2, 3, 4]
    frame2["Var A"] = [2.01, 0.013, -55.06, 0.04, 0.001]
    frame2["Var B"] = [2.01, 0.013, -55.06, 0.04, 0.001]
    frame2["Var C"] = [2.01, 0.013, -55.06, 0.04, 0.001]

    # same numbers, same deviations, various tolerance settings
    # Var C, default tolerance:
    #    absolute errors in 0 and 2, relative errors in 0 and 3
    # Var B, larger relative tolerance:
    #    absolute errors in 0 and 2
    # Var A, larger absolute tolerance:
    #    relative errors in 0 and 3
    tol: Dict[str, Tuple[np.float_, np.float_]] = {
        "default": (1.0, 0.1),
        "Var A": (10.0, 0.1),
        "Var B": (1.0, 1000),
    }

    absfailedndx, relfailedndx, failed = diff_per_column_dataframe(frame1, frame2, tol)
    assert absfailedndx == {"Var A": [], "Var B": [0, 2], "Var C": [0, 2]}
    assert relfailedndx == {"Var A": [0, 3], "Var B": [], "Var C": [0, 3]}
    assert failed == {
        "Var A": (False, True),
        "Var B": (True, False),
        "Var C": (True, True),
    }
