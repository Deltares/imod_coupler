from typing import Any

import numpy as np
from numpy.typing import NDArray


class Array:
    """
    This class handles the MODFLOW 6 pointers and transforms them
    from internal id's to user-id's and 3D shape (lay, row, col).

    ptr: pointer with shape (n_active_nodes)
    flat: arrays with shape (n_user_nodes)

    """

    ptr: NDArray[Any]
    flat: NDArray[Any]

    def __init__(
        self,
        nlay: int,
        nrow: int,
        ncol: int,
        userid: NDArray[Any],
        ptr: NDArray[Any],
    ) -> None:
        self.nlay = nlay
        self.nrow = nrow
        self.ncol = ncol
        self._set_ids(userid)
        self.flat = np.zeros((self.nlay * self.nrow * self.ncol), dtype=np.float64)
        self.ptr = ptr

    def update(self) -> None:
        """
        updates flat array with pointer values
        """
        self.flat[self.userid] = self.ptr

    def set_ptr(self, new_values: NDArray[Any]) -> None:
        """
        sets pointer(n_active_nodes) with new values(n_user_nodes)
        """
        valid = np.nonzero(new_values)
        self.ptr[:] = new_values[valid]

    def _set_ids(self, userid: NDArray[Any]) -> None:
        self.userid = userid - 1
        self.modelid = np.full((self.nlay * self.nrow * self.ncol), np.nan)
        self.modelid[self.userid] = np.arange(self.userid.size)

    @property
    def broadcasted(self) -> NDArray[Any]:
        return self.flat.reshape((self.nlay, self.nrow, self.ncol))

    @property
    def sum(self) -> NDArray[Any]:
        return np.sum(self.broadcasted, axis=0)


class BoundaryConditionArray(Array):
    """
    This class handles the MODFLOW 6 pointers for boundary condition packages. The class handles
    the extra transformation from list-oriented arrays to the model domain and back.
    """

    nodelist: NDArray[Any]

    def __init__(
        self,
        nlay: int,
        nrow: int,
        ncol: int,
        userid: NDArray[Any],
        ptr: NDArray[Any],
        nodelist: NDArray[Any],
    ) -> None:
        self.nodelist = nodelist
        super().__init__(nlay, nrow, ncol, userid, ptr)

    def update(self) -> None:
        """
        updates flat array with package values. The flat array is of shape user_nodes.
        The packages values are mapped using:

        1- package nodeslist: package list to modeldomain(active_nodes)
        2- userid: modeldomain(active_nodes) to modeldomain(user_nodes)

        """
        model_index = self.nodelist - 1
        # remove invalid indices in case package nbound < maxbound
        valid_index = model_index >= 0
        model_index = model_index[valid_index]
        # zero array in case current nbound < previous nbound
        self.flat[:] = 0.0
        self.flat[self.userid[model_index]] = self.ptr[:, 0][valid_index]

    def set_ptr(self, new_values: NDArray[Any]) -> None:
        """
        Sets package pointers. This includes:

        1- The package bounds array with boundary condition values
        2- The package nodeslist for mapping to modeldomain

        """
        valid = np.nonzero(new_values)
        self.ptr[:, 0] = new_values[valid]
        self.nodelist[:] = new_values[valid]


class PhreaticArray:
    row_indices: NDArray[Any]
    col_indices: NDArray[Any]

    def __init__(
        self,
        nlay: int,
        nrow: int,
        ncol: int,
        userid: NDArray[Any],
        ptr_saturation: NDArray[Any],
        ptr_package: NDArray[Any],
    ) -> None:
        self.nlay = nlay
        self.nrow = nrow
        self.ncol = ncol
        self.row_indices = np.repeat(np.arange(nrow), ncol)
        self.col_indices = np.tile(np.arange(ncol), reps=nrow)
        self.model_condition = Array(
            nlay=nlay, nrow=nrow, ncol=nrow, userid=userid, ptr=ptr_package
        )
        self.saturation = Array(
            nlay=nlay, nrow=nrow, ncol=nrow, userid=userid, ptr=ptr_saturation
        )

    def update(self) -> None:
        self.model_condition.update()
        self.saturation.update()

    @property
    def phreatic_layer_indices(self) -> Any:
        return np.argmax(self.saturation.broadcasted > 0, axis=0).flatten()

    @property
    def phreatic_values(self) -> Any:
        return self.model_condition.broadcasted[
            self.phreatic_layer_indices, self.row_indices, self.col_indices
        ]


class PhreaticPackage(PhreaticArray):
    def __init__(
        self,
        nlay: int,
        nrow: int,
        ncol: int,
        userid: NDArray[Any],
        ptr_saturation: NDArray[Any],
        ptr_package: NDArray[Any],
    ) -> None:
        self.nlay = nlay
        self.nrow = nrow
        self.ncol = ncol
        super().__init__(nlay, nrow, ncol, userid, ptr_saturation, ptr_package)

    def set_pointer(self, array: NDArray[Any]) -> None:
        self.model_condition.set_ptr(array)


class PhreaticBCPackage(PhreaticArray):
    """
    This class assigns boundary condition values to the phreatic layer
    based on the node saturation. The phreatic layer is defined at the top node
    with a saturation > 0.0, along dimension layer.
    """

    def __init__(
        self,
        nlay: int,
        nrow: int,
        ncol: int,
        userid: NDArray[Any],
        ptr_saturation: NDArray[Any],
        ptr_bc: NDArray[Any],
        ptr_bc_nodelist: NDArray[Any],
    ) -> None:
        self.nlay = nlay
        self.nrow = nrow
        self.ncol = ncol
        super().__init__(nlay, nrow, ncol, userid, ptr_saturation, ptr_bc)
        self.model_condition = BoundaryConditionArray(
            nlay=nlay,
            nrow=nrow,
            ncol=nrow,
            userid=userid,
            ptr=ptr_bc,
            nodelist=ptr_bc_nodelist,
        )
