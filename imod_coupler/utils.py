import os
from contextlib import contextmanager

import numpy as np
from scipy import sparse
from pathlib import Path


def read_mapping(map_file: str, nsrc: int, ntgt: int, operator: str, swap: bool):
    """Read the mapping from file, constructs a sparse matrix of size ntgt x nsrc
    and creates a mask array with 0 for mapped entries and 1 otherwise. The mask
    allows to update the target array without overwriting the unmapped entries
    with zeroes:
    
    target = mask * target + mapping * source
    
    Parameters
    ----------
    map_file : the file with the mapping
    nsrc : int
        the number of entries in the source array
    ntgt : int
        the number of entries in the target array
    operator : str
       indicating how n-1 mappings should be dealt
       with: "avg" for average, "sum" for sum
    swap : bool
        when true, the columns and rows from the mapping file are reversed

    Returns
    -------
    Tuple
        containing the mapping (csr_matrix) and a mask (numpy array)
    """

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
    map_out = sparse.csr_matrix((dat, (row, col)), shape=(ntgt, nsrc))
    mask = np.array([0 if i > 0 else 1 for i in map_out.getnnz(axis=1)])
    return map_out, mask


@contextmanager
def cd(path):
    """Changes working directory and returns to previous on exit."""
    prev_cwd = Path.cwd()
    path = Path(path)
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)
