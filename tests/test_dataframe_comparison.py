import numpy as np
import pandas as pd
from test_utilities import numeric_dataframes_equal


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
