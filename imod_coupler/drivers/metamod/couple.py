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
        ptr_a_conversion: NDArray[np.float64] | float | None = None,
        ptr_b_conversion: NDArray[np.float64] | float | None = None,
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
        ptr_a_conversion: NDArray[np.float64] | float | None = None,
        ptr_b_conversion: NDArray[np.float64] | float | None = None,
    ) -> None:
        if ptr_a_conversion is None and ptr_b_conversion is None:
            self.conversion_term = None
        else:
            conversion_term = np.ones_like(self.ptr_b, dtype=np.float64)
            if ptr_a_conversion is not None:
                conversion_term = ptr_a_conversion * conversion_term  # force to array
            if ptr_b_conversion is not None:
                conversion_term = conversion_term / ptr_b_conversion
            self.exchange_operator = (
                None  # effect of operator should be in conversion term
            )
            self.conversion_term = conversion_term

    def exchange(self) -> None:
        """Exchange Kernel a to Kernel b"""
        self.ptr_b[:] = self.mask[:] * self.ptr_b[:] + self.mapping.dot(self.ptr_a)[:]

    def log(self, label: str, time: float) -> None:
        """Log the exchange for receiving side; array b"""
        self.exchange_logger.log_exchange(label, self.ptr_b[:], time)

    def finalize_log(self) -> None:
        self.exchange_logger.finalize()
