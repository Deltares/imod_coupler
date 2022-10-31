from __future__ import annotations

from contextlib import contextmanager
from os import chdir
from pathlib import Path
from sys import stderr
from typing import Any, Tuple

import numpy as np
from loguru import logger
from numpy.typing import NDArray
from scipy.sparse import csr_matrix

from imod_coupler.config import LogLevel


def create_mapping(
    src_idx: Any, tgt_idx: Any, nsrc: int, ntgt: int, operator: str
) -> Tuple[csr_matrix, NDArray[np.int_]]:
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
        The indexes in the source array, zero-based
    tgt_idx : int
        The indexes in the target array, zero-based
    nsrc : int
        The number of entries in the source array
    ntgt : int
        The number of entries in the target array
    operator : str
       Indicating how n-1 mappings should be dealt
       with: "avg" for average, "sum" for sum.
       Operator does not affect 1-n couplings.

    Returns
    -------
    Tuple
        containing the mapping (csr_matrix) and a mask (numpy array)
    """
    if operator == "avg":
        cnt = np.zeros(max(tgt_idx) + 1)
        for i in range(len(tgt_idx)):
            cnt[tgt_idx[i]] += 1
        dat = np.array([1.0 / cnt[xx] for xx in tgt_idx])
    elif operator == "sum":
        dat = np.ones(tgt_idx.shape)
    else:
        raise ValueError("`operator` should be either 'sum' or 'avg'")
    map_out = csr_matrix((dat, (tgt_idx, src_idx)), shape=(ntgt, nsrc))
    mask = np.array([0 if i > 0 else 1 for i in map_out.getnnz(axis=1)])
    return map_out, mask


def setup_logger(log_level: LogLevel, log_file: Path) -> None:
    # Remove default handler
    logger.remove()

    # Add handler for stderr
    logger.add(
        stderr,
        colorize=True,
        format="iMOD Coupler: <level>{message}</level>",
        level=log_level,
    )

    # Add handler for file
    log_file.unlink(missing_ok=True)
    logger.add(log_file, level=log_level)


@contextmanager
def cd(newdir: Path):
    prevdir = Path().cwd()
    chdir(newdir)
    try:
        yield
    finally:
        chdir(prevdir)
