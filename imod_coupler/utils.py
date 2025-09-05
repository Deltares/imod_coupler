from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from os import chdir
from pathlib import Path
from sys import stderr
from typing import Any

import numpy as np
from loguru import logger
from numpy.typing import NDArray
from scipy.sparse import csr_matrix

from imod_coupler.config import LogLevel
from imod_coupler.logging.exchange_collector import ExchangeCollector

def create_mapping(
    src_idx: Any,
    tgt_idx: Any,
    nsrc: int,
    ntgt: int,
    operator: str | None = None,
    weights: NDArray[np.float64] | None = None,
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
        The indexes in the source array, zero-based
    tgt_idx : int
        The indexes in the target array, zero-based
    nsrc : int
        The number of entries in the source array
    ntgt : int
        The number of entries in the target array
    operator : str, optional
       Indicating how n-1 mappings should be dealt
       with: "avg" for average, "sum" for sum.
       Operator does not affect 1-n couplings.
    weights : NDArray[np.float64], optional
        User defined weights used in the sparse matrix

    Returns
    -------
    Tuple
        containing the mapping (csr_matrix) and a mask (numpy array)
    """
    if operator is None and weights is not None:
        dat = weights
    elif operator is not None and weights is None:
        if operator == "avg" and weights is None:
            cnt = np.zeros(max(tgt_idx) + 1)
            for i in range(len(tgt_idx)):
                cnt[tgt_idx[i]] += 1
            dat = np.array([1.0 / cnt[xx] for xx in tgt_idx])
        elif operator == "sum" and weights is None:
            dat = np.ones(tgt_idx.shape)
        else:
            raise ValueError("`operator` should be either 'sum' or 'avg'")
    else:
        raise ValueError("either `operator` or 'weights' should be defined")
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


class MemoryExchange:
    """Class to handle n:m exchanges between two pointers arrays"""

    def __init__(
        self,
        ptr_a: NDArray[np.float64 | np.int32],
        ptr_b: NDArray[np.float64 | np.int32],
        ptr_a_index: NDArray[np.int32],
        ptr_b_index: NDArray[np.int32],
        exchange_logger: ExchangeCollector,
        ptr_a_conversion: NDArray[np.float64] | None = None,
        ptr_b_conversion: NDArray[np.float64] | None = None,
        exchange_operator: str | None = None,
    ) -> None:
        self.ptr_a = ptr_a
        self.ptr_b = ptr_b
        self.ptr_a_index = ptr_a_index
        self.ptr_b_index = ptr_b_index
        self.exchange_logger = exchange_logger
        self.exchange_operator = exchange_operator
        self._set_conversion_terms(ptr_a_conversion, ptr_b_conversion)
        self.mapping, self.mask = create_mapping(
            self.ptr_a_index,
            self.ptr_b_index,
            self.ptr_a.size,
            self.ptr_b.size,
            self.exchange_operator,
            self.conversion_term,
        )

    def _set_conversion_terms(
        self,
        ptr_a_conversion: NDArray[np.float64] | None = None,
        ptr_b_conversion: NDArray[np.float64] | None = None,
    ) -> None:
        if ptr_a_conversion is None and ptr_b_conversion is None:
            self.conversion_term = None
        else:
            conversion_term = np.ones_like(self.ptr_a_index, dtype=np.float64)
            if ptr_a_conversion is not None:
                self._raise_if_not_compatible(ptr_a_conversion, self.ptr_a)
                conversion_term = ptr_a_conversion[self.ptr_a_index]
            if ptr_b_conversion is not None:
                self._raise_if_not_compatible(ptr_b_conversion, self.ptr_b)
                conversion_term = conversion_term * ptr_b_conversion[self.ptr_b_index]
            self.exchange_operator = (
                None  # effect of operator should be in conversion term
            )
            self.conversion_term = conversion_term

    def _raise_if_not_compatible(self, array1:NDArray[np.float64], array2:NDArray[np.float64]) -> None:
        if array1.shape != array2.shape:
            raise ValueError(
                "conversion array should have the same shape as corresponding ptr"
            )
        
    def exchange(self, delt: np.float64 = 1.0) -> None:
        """Exchange Kernel a to Kernel b"""
        self.ptr_b[:] = self.mask[:] * self.ptr_b[:] + self.mapping.dot(self.ptr_a)[:] / delt

    def log(self, label: str, time: float) -> None:
        """Log the exchange for receiving side; array b"""
        self.exchange_logger.log_exchange(label, self.ptr_b[:], time)
        self.label = label

    def finalize_log(self) -> None:
        """finalizes the exchange within the logger, if present"""
        if self.label in self.exchange_logger.exchanges.keys():
            self.exchange_logger.exchanges[self.label].finalize()


@contextmanager
def cd(newdir: Path) -> Iterator[None]:
    prevdir = Path().cwd()
    chdir(newdir)
    try:
        yield
    finally:
        chdir(prevdir)
