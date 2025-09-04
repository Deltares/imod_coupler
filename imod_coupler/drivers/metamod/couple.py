import numpy as np
from numpy.typing import NDArray

from imod_coupler.logging.exchange_collector import ExchangeCollector
from imod_coupler.utils import create_mapping


class Couple:
    """Class to exchange between two XMI kernels"""

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

    def finalize_log(self) -> None:
        self.exchange_logger.finalize()
