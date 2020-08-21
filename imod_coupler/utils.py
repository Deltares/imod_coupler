import os
from contextlib import contextmanager

import numpy as np
from scipy import sparse


def read_mapping(map_file: str, nsrc: int, ntgt: int, operator: str, swap: bool):
    map_arr = np.loadtxt(map_file, dtype=np.int32)
    # 1-based indices (fortran) to 0-based indices (python)
    if swap:
        col = map_arr[:, 0] - 1
        row = map_arr[:, 1] - 1
    else:
        row = map_arr[:, 0] - 1
        col = map_arr[:, 1] - 1
    if operator == "avg":
        cnt = np.zeros(max(row) + 1)
        for i in range(col.size):
            cnt[row[i]] += 1
        dat = np.array([1.0 / cnt[xx] for xx in row])
    if operator == "sum":
        dat = np.array([1.0 for xx in row])
    map_out = sparse.csr_matrix((dat, (row, col)), shape=(nsrc, ntgt))
    return map_out


@contextmanager
def cd(newdir):
    prevdir = os.getcwd()
    os.chdir(os.path.expanduser(newdir))
    try:
        yield
    finally:
        os.chdir(prevdir)
