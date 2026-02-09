from typing import Any, cast

import numpy as np
from numpy.typing import NDArray


class ExpandArray:
    """
    This class handles the MODFLOW 6 internal arrays and transforms them
    from internal (reduced) size to user size and 3D shape (layer, row, col). This is
    necessary in case of remapping to underlying layers.

    Relative from the users input, the internal arrays are reduces in two ways:
    1- Reduction due to inactive model nodes (idomain != 1)
    2- Subset of model nodes for boundary condition package arrays.

    Parameters
    ----------
    shape: tuple[int, int, int]:    tuple of grid dimensions layer, row and column
    userid (NDArray[Any]):          array with user id's (zero based) for reduced model nodes,
                                    relative to the user defined array
    ptr (NDArray[Any]):             pointer array with variable values (reduced size)
    ptr_nodelist (NDArray[Any]):    optional pointer array for bc-packages to map package nodes to (user defined) modelnodes

    """

    reduced: NDArray[Any]
    reduced_index: NDArray[np.int32]
    non_reduced: NDArray[Any]
    nlay: int
    nrow: int
    ncol: int

    def __init__(
        self,
        shape: tuple[int, int, int],
        userid: NDArray[Any],
        ptr: NDArray[Any],
        ptr_nodelist: NDArray[Any] | None = None,
    ) -> None:
        self.nlay, self.nrow, self.ncol = shape
        self._set_userid(userid)
        self._set_modelid()
        self.reduced = ptr
        self.non_reduced = np.full(
            (self.nlay * self.nrow * self.ncol), fill_value=np.nan, dtype=np.float64
        )
        self.nodelist = ptr_nodelist

    def _set_userid(self, userid: NDArray[Any]) -> None:
        self.userid = userid
        _, count = np.unique(self.userid, return_counts=True)
        assert np.all(count == 1)  # in case of n-m coupling, use only one rch element!

    def _set_modelid(self) -> None:
        """
        idomain
        layer 1  | 0 | 1 | 1  |
        layer 2  | 0 | 1 | 1  |
        layer 3  | 1 | 1 | 0  |  .

        user nodes                 model nodes
        layer 1  | 0 | 1 | 2  |    layer 1  |   | 0 | 1  |
        layer 2  | 3 | 4 | 5  |    layer 2  |   | 2 | 3  |
        layer 3  | 6 | 7 | 8  |    layer 3  | 4 | 5 |    |

        The userid array contains the mapping from model nodes back to the user defined nodes
        This function maps the reduced array index to a position in the non-reduced (user defined) array
        """
        self.reduced_index = np.full(
            (self.nlay * self.nrow * self.ncol), -1, dtype=np.int32
        )
        self.reduced_index[self.userid] = np.arange(self.userid.size)

    def to_full(self) -> NDArray[Any]:
        """
        Puts internal(reduced) array values in non-reduced (user defined) array
        """
        if self.nodelist is not None:
            # boundary condition package; userid based on package nodelist,
            # which is relative to the userid's
            modelid = self.nodelist - 1
            self.non_reduced[self.userid[modelid]] = self.reduced[:]
        else:
            self.non_reduced[self.userid] = self.reduced[:]
        return self.non_reduced

    def to_full_3d(self) -> NDArray[Any]:
        """
        Puts internal(reduced) array values in user-defined array,
        and returns 3D-vieuw
        """
        return self.to_full().reshape((self.nlay, self.nrow, self.ncol))


class PhreaticModelArray:
    """
    This class set and gets phreatic elements from the pointer arrays for internal flow-packages.
    The initial nodelist gives the 'coupled' selection of nodes of the first model layer.
    Based on the node saturation, the coresponding underlying phreatic nodes are selected
    to get or set values.

                                initial selection of nodes
                                     | * | * | * |   |

                  heads                phreatic nodes
    layer 1  | -|   |   |   |        | * |   |   |   |
    layer 2  |  | - |   |   |        |   | * |   |   |
    layer 3  |  |   | - | - |        |   |   | * |   |

    Parameters
    ----------
    shape: tuple[int, int, int]:    tuple of grid dimensions layer, row and column
    userid (NDArray[Any]):          array with user id's (zero based) for reduced model nodes,
    ptr_saturation (NDArray[Any]):  pointer array with saturation on reduced model nodes
    ptr_variable (NDArray[Any]):    pointer array with variable values on reduced model nodes
    node_idx (NDArray[Any]):        selection of coupled nodes in first model layer, for which the
                                    corresponding phreatic nodes are computed (zero based)
    max_layer (NDArray[Any]|None):  optional array with maximum layer (zero based) index for each node
    """

    variable: ExpandArray
    saturation: ExpandArray
    node_idx: NDArray[Any]
    row_user_index: NDArray[Any]
    col_user_index: NDArray[Any]
    initialised: bool
    max_layer_idx: NDArray[np.int32]

    def __init__(
        self,
        shape: tuple[int, int, int],
        userid: NDArray[Any],
        ptr_saturation: NDArray[Any],
        ptr_variable: NDArray[Any],
        node_idx: NDArray[Any],
        max_layer_idx: NDArray[np.int32],
    ) -> None:
        self.nlay, self.nrow, self.ncol = shape
        self.variable = ExpandArray(shape, userid, ptr_variable)
        self.saturation = ExpandArray(shape, userid, ptr_saturation)
        self.initialised = False
        self.node_idx = node_idx
        self.max_layer_idx = max_layer_idx

    def _ensure_user_indices(self) -> None:
        """
        Computes the row and column indices for the user shape 3D array. For boundary
        condition packages, the nodes array is only filled after the first prepare_timestep call

        considering inheritance, this method is therfore not called from the constructor
        """
        if self.initialised:
            return
        self.row_user_index = np.repeat(np.arange(self.nrow), self.ncol)[self.node_idx]
        self.col_user_index = np.tile(np.arange(self.ncol), reps=self.nrow)[
            self.node_idx
        ]
        self.initialised = True

    def set_at_phreatic(self, new_values: NDArray[Any]) -> None:
        """
        Sets the new values at the phreatic nodes

        Args:
            new_values (NDArray[Any]): new values at nodes selection
        """
        self.variable.reduced[self.phreatic_reduced_idx] = new_values

    def get_at_phreatic(self) -> NDArray[Any]:
        """
        Gets the variable values at the phreatic nodes

        Returns:
            NDArray[Any]: Array with variable values at phreatic nodes of initial nodes selection
        """
        return cast(
            NDArray[Any],
            self.variable.to_full_3d()[
                self.phreatic_layer_idx,
                self.row_user_index,
                self.col_user_index,
            ].flatten(),
        )

    @property
    def phreatic_layer_idx(self) -> NDArray[Any]:
        # TODO: use max layer from input in case of dry columns?
        self._ensure_user_indices()
        phreatic_layer: NDArray[np.int32] = (
            np.argmax(self.saturation.to_full_3d() > 0, axis=0)
            .astype(np.int32)
            .flatten()[self.node_idx]
        )
        # np.argmax returns an integer array (np.intp); ensure the result has a
        # consistent integer dtype for further indexing and satisfy mypy.
        phreatic_layer_max: NDArray[np.int32] = np.minimum(
            phreatic_layer, self.max_layer_idx
        ).astype(np.int32)
        return phreatic_layer_max

    @property
    def phreatic_reduced_idx(self) -> NDArray[np.int32]:
        phreatic_reduced_index = self.variable.reduced_index.reshape(
            (self.nlay, self.nrow, self.ncol)
        )[
            self.phreatic_layer_idx,
            self.row_user_index,
            self.col_user_index,
        ].flatten()
        assert np.all(phreatic_reduced_index >= 0)
        return cast(NDArray[np.int32], phreatic_reduced_index)


class PhreaticBCArray:
    """
    This class sets the pointer arrays for the boundary condition-packages. In adition to the
    PhreaticModelArray-class it sets the package nodelist pointer to the corresponing phreatic nodes.

    This class set and gets phreatic elements from the pointer arrays for model-packages.
    The initial nodelist gives the 'coupled' selection of nodes of the first model layer.
    Based on the node saturation, the coresponding underlying phreatic nodes are selected
    to get or set values.
    """

    initial_nodes_idx: NDArray[Any]
    max_layer_idx: NDArray[np.int32]

    def __init__(
        self,
        shape: tuple[int, int, int],
        userid: NDArray[Any],
        ptr_saturation: NDArray[Any],
        ptr_package_variable: NDArray[Any],
        ptr_package_nodelist: NDArray[Any],
        max_layer_idx: NDArray[np.int32],
    ) -> None:
        self.nlay, self.nrow, self.ncol = shape
        self.variable = ExpandArray(
            shape,
            userid,
            ptr_package_variable,
            ptr_package_nodelist,
        )
        self.saturation = ExpandArray(shape, userid, ptr_saturation)
        self.nodes_ptr = ptr_package_nodelist  # used for nodes after prepare_timestep
        self.initialised = False
        self.max_layer_idx = max_layer_idx

    def _ensure_user_indices(self) -> None:
        # the nodelist for bc-packages is only filled after the first prepare-timestep call
        # This method therefore is not called from the constructor
        if not self.initialised:
            self.nodes_idx = self.nodes_ptr - 1
            userid = self.variable.userid
            self.row_user_index = np.repeat(np.arange(self.nrow), self.ncol)[
                userid[self.nodes_idx]
            ]
            self.col_user_index = np.tile(np.arange(self.ncol), reps=self.nrow)[
                userid[self.nodes_idx]
            ]
            self.initial_nodes_idx = np.copy(self.nodes_idx)
            self.initialised = True

    def set_at_phreatic(self, new_values: NDArray[Any]) -> None:
        # the variable values does not need to be mapped, since the nodelist points to the phreatic nodes
        self.variable.reduced[:] = new_values[:]
        if self.variable.nodelist is None:
            raise RuntimeError("package nodelist is not initialised")
        self.variable.nodelist[:] = (self.phreatic_reduced_idx + 1)[:]

    @property
    def phreatic_layer_idx(self) -> NDArray[Any]:
        # self._ensure_user_indices()
        # use initial_nodes since self.nodes is updated by set_ptr method
        phreatic_layer: NDArray[np.int32] = (
            np.argmax(self.saturation.to_full_3d() > 0, axis=0)
            .astype(np.int32)
            .flatten()[self.variable.userid[self.initial_nodes_idx]]
        )
        # ensure a consistent integer dtype for indexing and satisfy mypy
        result: NDArray[np.int32] = np.minimum(
            phreatic_layer, self.max_layer_idx
        ).astype(np.int32)
        return result

    @property
    def phreatic_reduced_idx(self) -> NDArray[np.int32]:
        self._ensure_user_indices()
        phreatic_reduced_index = self.variable.reduced_index.reshape(
            (self.nlay, self.nrow, self.ncol)
        )[
            self.phreatic_layer_idx,
            self.row_user_index,
            self.col_user_index,
        ].flatten()
        assert np.all(phreatic_reduced_index >= 0)
        return cast(NDArray[np.int32], phreatic_reduced_index)


class PhreaticStorage:
    """
    Wrapper class for STO-package of MODFLOW 6. Contains methods for:

    1- Setting values to phreatic nodes of SY and zeros the corresponding SS values
    2- Resetting both SY and SS arrays to initial values
    """

    sy: PhreaticModelArray
    ss: PhreaticModelArray
    zeros: NDArray[Any]
    initial_sy: NDArray[Any]
    initial_ss: NDArray[Any]

    def __init__(
        self,
        shape: tuple[int, int, int],
        userid: NDArray[Any],
        ptr_saturation: NDArray[Any],
        ptr_storage_sy: NDArray[Any],
        ptr_storage_ss: NDArray[Any],
        active_top_layer_node_idx: NDArray[Any],
        max_layer: NDArray[np.int32],
    ) -> None:
        self.zeros = np.zeros(active_top_layer_node_idx.size)
        self.initial_sy = np.copy(ptr_storage_sy)
        self.initial_ss = np.copy(ptr_storage_ss)
        self.sy = PhreaticModelArray(
            shape,
            userid,
            ptr_saturation,
            ptr_storage_sy,
            active_top_layer_node_idx,
            max_layer,
        )
        self.ss = PhreaticModelArray(
            shape,
            userid,
            ptr_saturation,
            ptr_storage_ss,
            active_top_layer_node_idx,
            max_layer,
        )

    def reset(self) -> None:
        self.sy.variable.reduced[:] = self.initial_sy[:]
        self.ss.variable.reduced[:] = self.initial_ss[:]

    def set(self, new_sy: NDArray[Any]) -> None:
        self.sy.set_at_phreatic(new_sy)
        self.ss.set_at_phreatic(self.zeros)


class PhreaticRecharge:
    """
    Wrapper class for RCH-package of MODFLOW 6. Contains methods for:

    - Setting recharge values and updating package-nodelist to current phreatic nodes
    """

    recharge: PhreaticBCArray

    def __init__(
        self,
        shape: tuple[int, int, int],
        userid: NDArray[Any],
        ptr_saturation: NDArray[Any],
        ptr_recharge: NDArray[Any],
        ptr_recharge_nodelist: NDArray[Any],
        max_layer_idx: NDArray[np.int32],
    ) -> None:
        self.recharge = PhreaticBCArray(
            shape,
            userid,
            ptr_saturation,
            ptr_recharge,
            ptr_recharge_nodelist,
            max_layer_idx,
        )

    def set(self, new_recharge: NDArray[Any]) -> None:
        self.recharge.set_at_phreatic(new_recharge)


class PhreaticHeads:
    """
    Wrapper class for heads of MODFLOW 6. Contains methods for:

    - Getting heads values for current phreatic nodes
    """

    heads: PhreaticModelArray

    def __init__(
        self,
        shape: tuple[int, int, int],
        userid: NDArray[Any],
        ptr_saturation: NDArray[Any],
        ptr_heads: NDArray[Any],
        active_top_layer_node_idx: NDArray[Any],
        max_layer_idx: NDArray[np.int32],
    ) -> None:
        self.heads = PhreaticModelArray(
            shape,
            userid,
            ptr_saturation,
            ptr_heads,
            active_top_layer_node_idx,
            max_layer_idx,
        )

    def get(self) -> NDArray[Any]:
        return self.heads.get_at_phreatic()
