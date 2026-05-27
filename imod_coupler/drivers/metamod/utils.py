from abc import ABC
from typing import Any

import numpy as np
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
        coupled_top_layer_nodes: NDArray[Any],  # zero based index array
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
            coupled_top_layer_nodes,
        )

    def exchange(self, time: float | None = None) -> None:
        self.storage.reset()  # reset befor setting the exchanged values
        self.coupling.exchange()  # exchange to top nodes
        self.storage.set(self.coupling.ptr_b)  # set to phreatic nodes


class CoupledPhreaticRecharge(CoupledBase):
    def __init__(
        self,
        shape: tuple[int, int, int],
        userid: NDArray[Any],
        ptr_saturation: NDArray[Any],
        ptr_recharge: NDArray[Any],
        ptr_recharge_nodelist: NDArray[Any],  # one based package nodelist
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


class CoupledUZF:
    def __init__(
        self,
        shape: tuple[int, int, int],
        new_recharge: NDArray[Any],
        head: NDArray[Any],
        infiltration_ptr: NDArray[Any],
        nodelist_ptr: NDArray[Any],
        userid: NDArray[Any],
        max_layer_index: NDArray[Any],
        first_layer_nodes: NDArray[Any],
        top: NDArray[Any],
        landflag: NDArray[Any],
    ) -> None:
        self.infiltration = infiltration_ptr
        self.nodelist = nodelist_ptr - 1  # adjust to zero based index
        self.top = top
        self.new_recharge = new_recharge
        self.head = head
        nlay, nrow, ncol = shape

        # create 3D index arrays
        mf6_index_2d = np.full((nlay * nrow * ncol), -1, dtype=np.int32)
        uzf_index_2d = np.full((nlay * nrow * ncol), -1, dtype=np.int32)
        # TODO check if UZF-nodelist is really relative to the user defined nodes
        mf6_index_2d[userid[self.nodelist] - 1] = self.nodelist
        uzf_index_2d[userid[self.nodelist] - 1] = np.arange(self.nodelist.size)

        # broadcast to 3D to find the top UZF nodes to apply the infiltration to
        mf6_index_2d = mf6_index_2d.reshape((nlay, nrow * ncol))
        uzf_index_2d = uzf_index_2d.reshape((nlay, nrow * ncol))
        # find uzf index (model nodes) based on the giver max layer(model nodes)
        max_layer_index = max_layer_index + 1
        max_layer_index[max_layer_index > nlay - 1] = nlay - 1

        mf6_index = mf6_index_2d[max_layer_index, first_layer_nodes - 1]
        uzf_index = uzf_index_2d[max_layer_index, first_layer_nodes - 1]

        self.mf6_rch_index = np.arange(mf6_index.size, dtype=np.int32)[
            mf6_index > -1
        ]  # projection to 2D (x,y) plane of rch grid
        self.mf6_index = mf6_index[mf6_index > -1]
        self.uzf_index = uzf_index[uzf_index > -1]

        # be sure to set landflag so we can set infiltration properly
        landflag[self.uzf_index] = 1
        # get active uzf nodes relative to the 2d plane of the rch grid
        self.uzf_active_mask = np.full_like(first_layer_nodes, False, dtype=bool)
        self.uzf_active_mask[self.mf6_rch_index] = True
        self.uzf_mask = np.copy(self.uzf_active_mask)

    def exchange(self, time: float | None = None) -> NDArray[np.bool]:
        self.infiltration[self.uzf_index] = 0.0
        self.uzf_mask[:] = self.uzf_active_mask[:]
        self.uzf_mask[self.mf6_rch_index] = (
            self.head[self.mf6_rch_index] < self.top[self.uzf_index]
        )
        self.infiltration[self.uzf_index] = (
            self.new_recharge[self.mf6_rch_index] * self.uzf_mask[self.mf6_rch_index]
        )[:]
        # set echanged values to zero in ptr
        self.new_recharge[self.mf6_rch_index] = 0.0
        return self.uzf_mask

    def log(self, time: float) -> None:
        pass

    def finalize_log(self) -> None:
        pass
