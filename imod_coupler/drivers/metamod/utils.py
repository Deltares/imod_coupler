from abc import ABC
from typing import Any

from numpy.typing import NDArray

from imod_coupler.kernelwrappers.mf6_newton_wrapper import (
    PhreaticHeads,
    PhreaticRecharge,
    PhreaticStorage,
)
from imod_coupler.utils import MemoryExchange


class CoupledBase(ABC):
    def __init__(self, coupling: MemoryExchange) -> None:
        self.coupling = coupling

    def exchange(self, time: float | None = None) -> None:
        pass

    def log(self, time: float) -> None:
        self.coupling.log(time)

    def finalize_log(self) -> None:
        self.coupling.finalize_log()


class CoupledPhreaticStorage(CoupledBase):
    def __init__(
        self,
        shape: tuple[int, int, int],
        userid: NDArray[Any],
        ptr_saturation: NDArray[Any],
        ptr_storage_sy: NDArray[Any],
        ptr_storage_ss: NDArray[Any],
        active_top_layer_nodes: NDArray[Any],
        max_layer: NDArray[Any],
        coupling: MemoryExchange,
    ) -> None:
        super().__init__(coupling)
        self.storage = PhreaticStorage(
            shape,
            userid,
            ptr_saturation,
            ptr_storage_sy,
            ptr_storage_ss,
            active_top_layer_nodes,
            max_layer,
        )

    def exchange(self, time: float | None = None) -> None:
        self.coupling.exchange()  # exchange to top nodes
        self.storage.reset()  # reset befor setting the exchanged values
        self.storage.set(self.coupling.ptr_b)  # set to phreatic nodes


class CoupledPhreaticRecharge(CoupledBase):
    def __init__(
        self,
        shape: tuple[int, int, int],
        userid: NDArray[Any],
        ptr_saturation: NDArray[Any],
        ptr_recharge: NDArray[Any],
        ptr_recharge_nodelist: NDArray[Any],
        max_layer: NDArray[Any],
        coupling: MemoryExchange,
    ) -> None:
        super().__init__(coupling)
        self.recharge = PhreaticRecharge(
            shape,
            userid,
            ptr_saturation,
            ptr_recharge,
            ptr_recharge_nodelist,
            max_layer,
        )

    def exchange(self, time: float | None = None) -> None:
        self.coupling.exchange()  # exchange to top nodes
        self.recharge.set(self.coupling.ptr_b)  # set to phreatic nodes


class CoupledPhreaticHeads(CoupledBase):
    def __init__(
        self,
        shape: tuple[int, int, int],
        userid: NDArray[Any],
        ptr_saturation: NDArray[Any],
        ptr_heads: NDArray[Any],
        active_top_layer_nodes: NDArray[Any],
        max_layer: NDArray[Any],
        coupling: MemoryExchange,
    ) -> None:
        super().__init__(coupling)
        self.heads = PhreaticHeads(
            shape,
            userid,
            ptr_saturation,
            ptr_heads,
            active_top_layer_nodes,
            max_layer,
        )

    def exchange(self, time: float | None = None) -> None:
        self.coupling.ptr_a = self.heads.get()  # get heads at phreatic nodes
        self.coupling.exchange()  # exchange to msw
