import numpy as np
import xarray as xr
from pytest_cases import case


def util_1_1_symmetric_sum():
    src_idx = np.array([0, 1, 2], dtype=int)
    tgt_idx = np.array([0, 1, 2], dtype=int)

    nsrc = 3
    ntgt = 3
    operator = "sum"

    expected_mask = np.array([0, 0, 0], dtype=int)
    expected_map_dense = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    return src_idx, tgt_idx, nsrc, ntgt, operator, expected_map_dense, expected_mask


def util_1_1_symmetric_avg():
    src_idx = np.array([0, 1, 2], dtype=int)
    tgt_idx = np.array([0, 1, 2], dtype=int)

    nsrc = 3
    ntgt = 3
    operator = "avg"

    expected_mask = np.array([0, 0, 0], dtype=int)
    expected_map_dense = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    return src_idx, tgt_idx, nsrc, ntgt, operator, expected_map_dense, expected_mask


def util_1_1_asymmetric_sum():
    src_idx = np.array([0, 1, 2], dtype=int)
    tgt_idx = np.array([2, 3, 4], dtype=int)

    nsrc = 3
    ntgt = 6
    operator = "sum"

    expected_mask = np.array([1, 1, 0, 0, 0, 1], dtype=int)
    expected_map_dense = np.array(
        [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 0.0],
        ]
    )
    return src_idx, tgt_idx, nsrc, ntgt, operator, expected_map_dense, expected_mask


def util_1_1_asymmetric_avg():
    src_idx = np.array([0, 1, 2], dtype=int)
    tgt_idx = np.array([2, 3, 4], dtype=int)

    nsrc = 3
    ntgt = 6
    operator = "avg"

    expected_mask = np.array([1, 1, 0, 0, 0, 1], dtype=int)
    expected_map_dense = np.array(
        [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 0.0],
        ]
    )
    return src_idx, tgt_idx, nsrc, ntgt, operator, expected_map_dense, expected_mask


def util_n_1_symmetric_sum():
    src_idx = np.array([0, 1, 2], dtype=int)
    tgt_idx = np.array([0, 1, 1], dtype=int)

    nsrc = 3
    ntgt = 3
    operator = "sum"

    expected_mask = np.array([0, 0, 1], dtype=int)
    expected_map_dense = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 1.0],
            [0.0, 0.0, 0.0],
        ]
    )
    return src_idx, tgt_idx, nsrc, ntgt, operator, expected_map_dense, expected_mask


def util_n_1_symmetric_avg():
    src_idx = np.array([0, 1, 2], dtype=int)
    tgt_idx = np.array([0, 1, 1], dtype=int)

    nsrc = 3
    ntgt = 3
    operator = "avg"

    expected_mask = np.array([0, 0, 1], dtype=int)
    expected_map_dense = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 0.5, 0.5],
            [0.0, 0.0, 0.0],
        ]
    )
    return src_idx, tgt_idx, nsrc, ntgt, operator, expected_map_dense, expected_mask


def util_n_1_asymmetric_sum():
    src_idx = np.array([0, 1, 2], dtype=int)
    tgt_idx = np.array([2, 2, 4], dtype=int)

    nsrc = 3
    ntgt = 6
    operator = "sum"

    expected_mask = np.array([1, 1, 0, 1, 0, 1], dtype=int)
    expected_map_dense = np.array(
        [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 0.0],
        ]
    )
    return src_idx, tgt_idx, nsrc, ntgt, operator, expected_map_dense, expected_mask


def util_n_1_asymmetric_avg():
    src_idx = np.array([0, 1, 2], dtype=int)
    tgt_idx = np.array([2, 2, 4], dtype=int)

    nsrc = 3
    ntgt = 6
    operator = "avg"

    expected_mask = np.array([1, 1, 0, 1, 0, 1], dtype=int)
    expected_map_dense = np.array(
        [
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [0.5, 0.5, 0.0],
            [0.0, 0.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, 0.0],
        ]
    )
    return src_idx, tgt_idx, nsrc, ntgt, operator, expected_map_dense, expected_mask


@case(tags="succeed")
def rch_2D(recharge):
    """
    Case where recharge is a 2D grid (y,x) and has a "layer" coord.
    """
    return recharge


@case(tags="succeed")
def rch_3D_layer_size_1(recharge):
    """
    Case where recharge has a third dimension "layer" with size one.
    """
    ds = recharge.dataset.expand_dims("layer").assign_coords(layer=[1])
    recharge.dataset = ds
    return recharge


@case(tags="fail")
def rch_3D(recharge):
    """
    Case where recharge assigned to multiple layers.
    """
    ds = recharge.dataset.drop_vars("layer")
    layer_data = xr.DataArray([1, 1, 1], coords={"layer": [1, 2, 3]}, dims=("layer",))
    ds["rate"] = layer_data * ds["rate"]
    recharge.dataset = ds
    return recharge


@case(tags="fail")
def rch_transient(recharge):
    """
    Case where rate has time dimension, should fail because mapping cannot
    change through time.
    """
    ds = recharge.dataset
    times_str = ["2000-01-01", "2000-01-02", "2000-01-03"]
    times = [np.datetime64(t) for t in times_str]
    time_data = xr.DataArray([1, 1, 1], coords={"time": times}, dims=("time",))
    ds["rate"] = time_data * ds["rate"]
    recharge.dataset = ds
    return recharge
