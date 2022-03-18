import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

import numpy as np
from numpy.typing import NDArray
from scipy.sparse import csr_matrix


def create_mapping(
    src_idx: Any, tgt_idx: Any, nsrc: int, ntgt: int, operator: str
) -> tuple[csr_matrix, NDArray[np.int_]]:
    """
    Create a mapping from source indexes to target indexes by constructing
    a sparse matrix of size (ntgt x nsrc) and creates a mask array with 0
    for mapped entries and 1 otherwise.
    The mask allows to update the target array without overwriting the unmapped
    entries with zeroes:

    target = mask * target + mapping * source

    Parameters
    ----------
    src_idx : int
        the indexes in the source array, zero-based
    tgt_idx : int
        the indexes in the target array, zero-based
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
    if operator == "avg":
        cnt = np.zeros(max(tgt_idx) + 1)
        for i in range(len(tgt_idx)):
            cnt[tgt_idx[i]] += 1
        dat: NDArray[Any] = np.array([1.0 / cnt[xx] for xx in tgt_idx])
    if operator == "sum":
        dat = np.array([1.0 for xx in tgt_idx])
    map_out = csr_matrix((dat, (tgt_idx, src_idx)), shape=(ntgt, nsrc))
    mask: NDArray[Any] = np.array([0 if i > 0 else 1 for i in map_out.getnnz(axis=1)])
    return map_out, mask


@contextmanager
def cd(path: Path) -> Generator[None, None, None]:
    """Changes working directory and returns to previous on exit."""
    prev_cwd = Path.cwd()
    path = Path(path)
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)
