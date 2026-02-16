import numpy as np
from numpy.typing import NDArray

from imod_coupler.logging.exchange_collector import ExchangeCollector
from imod_coupler.utils import MemoryExchange


class MemoryExchangeFractions(MemoryExchange):
    def __init__(
        self,
        ptr_a_fractions: NDArray[np.float64 | np.int32],
        ptr_b: NDArray[np.float64 | np.int32],
        ptr_bb: NDArray[np.float64 | np.int32],
        ptr_a_index: NDArray[np.int32],
        ptr_b_index: NDArray[np.int32],
        exchange_logger: ExchangeCollector,
        label: str,
        ptr_a_conversion: NDArray[np.float64] | None = None,
        ptr_b_conversion: NDArray[np.float64] | None = None,
        exchange_operator: str | None = None,
    ) -> None:
        self.ptr_bb = ptr_bb
        super().__init__(
            ptr_a_fractions,
            ptr_b,
            ptr_a_index,
            ptr_b_index,
            exchange_logger,
            label,
            ptr_a_conversion,
            ptr_b_conversion,
            exchange_operator,
        )

    def exchange(self, delt: float = 1.0) -> None:
        """Exchange Kernel a to Kernel b"""
        self.ptr_b[:] = self.ptr_bb * self.mapping.dot(self.ptr_a)


class MemoryExchangePositiveFractions(MemoryExchange):
    def __init__(
        self,
        ptr_a: NDArray[np.float64 | np.int32],
        ptr_b: NDArray[np.float64 | np.int32],
        ptr_a_index: NDArray[np.int32],
        ptr_b_index: NDArray[np.int32],
        exchange_logger: ExchangeCollector,
        label: str,
        ptr_a_conversion: NDArray[np.float64] | None = None,
        ptr_b_conversion: NDArray[np.float64] | None = None,
        exchange_operator: str | None = None,
    ) -> None:
        super().__init__(
            ptr_a,
            ptr_b,
            ptr_a_index,
            ptr_b_index,
            exchange_logger,
            label,
            ptr_a_conversion,
            ptr_b_conversion,
            exchange_operator,
        )

    def exchange(self, delt: float = 1.0) -> None:
        """Exchange Kernel a to Kernel b"""
        self.ptr_a[:] = np.where(self.ptr_a > 0, self.ptr_a, 0)[:]
        self.ptr_b[:] = (
            self.mask[:] * self.ptr_b[:] + self.mapping.dot(self.ptr_a)[:] / delt
        )


class MemoryExchangeNegativeFractions(MemoryExchange):
    def __init__(
        self,
        ptr_a_fractions: NDArray[np.float64 | np.int32],
        ptr_b: NDArray[np.float64 | np.int32],
        ptr_bb: NDArray[np.float64 | np.int32],
        ptr_a_index: NDArray[np.int32],
        ptr_b_index: NDArray[np.int32],
        exchange_logger: ExchangeCollector,
        label: str,
        ptr_a_conversion: NDArray[np.float64] | None = None,
        ptr_b_conversion: NDArray[np.float64] | None = None,
        exchange_operator: str | None = None,
    ) -> None:
        self.ptr_bb = ptr_bb
        super().__init__(
            ptr_a_fractions,
            ptr_b,
            ptr_a_index,
            ptr_b_index,
            exchange_logger,
            label,
            ptr_a_conversion,
            ptr_b_conversion,
            exchange_operator,
        )

    def exchange(self, delt: float = 1.0) -> None:
        """Exchange Kernel a to Kernel b"""
        self.ptr_b[:] = (np.maximum(self.ptr_bb / delt, 0.0)) * (
            1 - self.mapping.dot(self.ptr_a)
        )
