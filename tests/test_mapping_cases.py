import numpy as np

from imod_coupler.utils import Operator


def case_1_1_symmetric_sum():
    src_idx = np.array([0, 1, 2], dtype=int)
    tgt_idx = np.array([0, 1, 2], dtype=int)

    nsrc = 3
    ntgt = 3
    operator = Operator.SUM

    expected_mask = np.array([0, 0, 0], dtype=int)
    expected_map_dense = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    return src_idx, tgt_idx, nsrc, ntgt, operator, expected_map_dense, expected_mask


def case_1_1_symmetric_avg():
    src_idx = np.array([0, 1, 2], dtype=int)
    tgt_idx = np.array([0, 1, 2], dtype=int)

    nsrc = 3
    ntgt = 3
    operator = Operator.AVERAGE

    expected_mask = np.array([0, 0, 0], dtype=int)
    expected_map_dense = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    return src_idx, tgt_idx, nsrc, ntgt, operator, expected_map_dense, expected_mask


def case_1_1_asymmetric_sum():
    src_idx = np.array([0, 1, 2], dtype=int)
    tgt_idx = np.array([2, 3, 4], dtype=int)

    nsrc = 3
    ntgt = 6
    operator = Operator.SUM

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


def case_1_1_asymmetric_avg():
    src_idx = np.array([0, 1, 2], dtype=int)
    tgt_idx = np.array([2, 3, 4], dtype=int)

    nsrc = 3
    ntgt = 6
    operator = Operator.AVERAGE

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


def case_n_1_symmetric_sum():
    src_idx = np.array([0, 1, 2], dtype=int)
    tgt_idx = np.array([0, 1, 1], dtype=int)

    nsrc = 3
    ntgt = 3
    operator = Operator.SUM

    expected_mask = np.array([0, 0, 1], dtype=int)
    expected_map_dense = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 1.0],
            [0.0, 0.0, 0.0],
        ]
    )
    return src_idx, tgt_idx, nsrc, ntgt, operator, expected_map_dense, expected_mask


def case_n_1_symmetric_avg():
    src_idx = np.array([0, 1, 2], dtype=int)
    tgt_idx = np.array([0, 1, 1], dtype=int)

    nsrc = 3
    ntgt = 3
    operator = Operator.AVERAGE

    expected_mask = np.array([0, 0, 1], dtype=int)
    expected_map_dense = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 0.5, 0.5],
            [0.0, 0.0, 0.0],
        ]
    )
    return src_idx, tgt_idx, nsrc, ntgt, operator, expected_map_dense, expected_mask


def case_n_1_asymmetric_sum():
    src_idx = np.array([0, 1, 2], dtype=int)
    tgt_idx = np.array([2, 2, 4], dtype=int)

    nsrc = 3
    ntgt = 6
    operator = Operator.SUM

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


def case_n_1_asymmetric_avg():
    src_idx = np.array([0, 1, 2], dtype=int)
    tgt_idx = np.array([2, 2, 4], dtype=int)

    nsrc = 3
    ntgt = 6
    operator = Operator.AVERAGE

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
