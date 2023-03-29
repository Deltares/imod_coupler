import numpy as np
import pandas as pd
from test_utilities import numeric_dataframes_equal, diff_per_column_dataframe


def test_compare_absolute_fail():
    frame1 = pd.DataFrame([[10, -10], [1, -1]])
    frame2 = pd.DataFrame([[10.01, -10.01], [1.01, -1.01]])

    assert not numeric_dataframes_equal(frame1, frame2, abstol=0.009, reltol=100)


def test_compare_absolute_succeed():
    frame1 = pd.DataFrame([[10, -10], [1, -1]])
    frame2 = pd.DataFrame([[10.01, -10.01], [1.01, -1.01]])

    assert numeric_dataframes_equal(frame1, frame2, abstol=0.011, reltol=100)


def test_compare_relative_fail():
    frame1 = pd.DataFrame([[10, -10], [1, -1]])
    frame2 = pd.DataFrame([[10.01, -10.01], [1.01, -1.01]])

    frame1 = pd.DataFrame([[10, -10], [1, -1]])
    assert not numeric_dataframes_equal(frame1, frame2, abstol=100, reltol=0.001)


def test_compare_relative_succeed():
    frame1 = pd.DataFrame([[10, -10], [1, -1]])
    frame2 = pd.DataFrame([[10.01, -10.01], [1.01, -1.01]])

    assert numeric_dataframes_equal(frame1, frame2, abstol=100, reltol=0.011)


def test_compare_with_nan():
    frame1 = pd.DataFrame([[np.nan, -10], [1, -1]])
    frame2 = pd.DataFrame([[np.nan, -10.01], [1.01, -1.01]])

    assert numeric_dataframes_equal(frame1, frame2, abstol=100, reltol=0.011)


def test_compare_with_nan_fails():
    frame1 = pd.DataFrame([[np.nan, -10], [1, -1]])
    frame2 = pd.DataFrame([[10, np.nan], [1, -1]])

    assert not numeric_dataframes_equal(frame1, frame2, abstol=100, reltol=0.011)


def test_compare_varying_tolerances():
    frame1 = pd.DataFrame()
    frame1["Var A"] = [0.01, 0.013, -50.06, -0.04, 0.001]
    frame1["Var B"] = [0.01, 0.013, -50.06, -0.04, 0.001]
    frame1["Var C"] = [0.01, 0.013, -50.06, -0.04, 0.001]

    frame2 = pd.DataFrame()
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
    tol = {
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
