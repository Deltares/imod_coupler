from typing import Any

import numpy as np
from numpy.typing import NDArray


class ExpandArray:
    """
    This class handles the MODFLOW 6 internal arrays and transforms them
    from internal size to user size and 3D shape (layer, row, col).

    Relative from the users input, the internal arrays are reduces in two ways:
    1- Reduction due to inactive model nodes (idomain != 1)
    2- Subset of model nodes for boundary condition package arrays.

    Parameters
    ----------
    shape: list[int, int, int]:     list that contains the grid demensions layer, row and column
    userid (NDArray[Any]):          array with user id's for model nodes
    ptr (NDArray[Any]):             pointer array with variable values on model nodes
    ptr_nodelist (NDArray[Any]):    optional pointer array for bc-packages to map package nodes to modelnodes

    """

    variable_model: NDArray[Any]
    variable_user: NDArray[Any]

    def __init__(
        self,
        shape: list[int],
        userid: NDArray[Any],
        ptr: NDArray[Any],
        ptr_nodelist: NDArray[Any] | None = None,
    ) -> None:
        self.nlay, self.nrow, self.ncol = shape
        self._set_userid(userid)
        self._set_modelid()
        self.variable_model = ptr
        self.variable_user = np.full(
            (self.nlay * self.nrow * self.ncol), fill_value=np.nan, dtype=np.float64
        )
        self.nodelist = ptr_nodelist

    def _set_modelid(self) -> None:
        """
        Sets array of 0-based modelid in user size
        """
        self.modelid = np.full(
            (self.nlay * self.nrow * self.ncol), np.nan, dtype=np.int32
        )
        self.modelid[self.userid] = np.arange(self.userid.size)

    def _set_userid(self, userid: NDArray[Any]) -> None:
        """
        Sets array of 0-based userid in model size
        """
        self.userid = userid - 1

    def _update(self) -> None:
        """
        updates variable array is user size with current pointer values from model sized array
        """
        if self.nodelist is not None:
            # boundary condition package; userid based on package nodelist,
            # which is relative to the userid's
            modelid = self.nodelist - 1
            self.variable_user[self.userid[modelid]] = self.variable_model[:]
        else:
            self.variable_user[self.userid] = self.variable_model[:]

    def broadcast(self) -> NDArray[Any]:
        """
        returns 3D variable array is user size
        """
        self._update()
        return self.variable_user.reshape((self.nlay, self.nrow, self.ncol))

    def expand(self) -> NDArray[Any]:
        """
        returns flat variable array in user size
        """
        self._update()
        return self.variable_user


class PhreaticModelArray:
    """
    This class set and gets phreatic elements from the pointer arrays for model-packages.
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
    shape: list[int, int, int]:     list that contains the grid demensions layer, row and column
    userid (NDArray[Any]):          array with user id's for model nodes
    ptr_saturation (NDArray[Any]):  pointer array with saturation on model nodes
    ptr_variable (NDArray[Any]):    pointer array with variable values on model nodes
    nodes (NDArray[Any]):           selection of nodes in first model layer, for which the
                                    corresponding phreaticnodes are computed
    """

    variable: ExpandArray
    saturation: ExpandArray
    nodes: NDArray[Any]
    row_user_indices: NDArray[Any]
    col_user_indices: NDArray[Any]
    initialised: bool

    def __init__(
        self,
        shape: list[int],
        userid: NDArray[Any],
        ptr_saturation: NDArray[Any],
        ptr_variable: NDArray[Any],
        nodes: NDArray[Any],
    ) -> None:
        self.nlay, self.nrow, self.ncol = shape
        self.variable = ExpandArray(shape, userid, ptr_variable)
        self.saturation = ExpandArray(shape, userid, ptr_saturation)
        self.initialised = False
        self.nodes = nodes - 1

    def _set_user_indices(self) -> None:
        """
        Computes the row and column indices for the user shape 3D array. For boundary
        condition packages, the nodes array is only filled after the first prepare_timestep call

        considering inheritance, this method is therfore not called from the constructor
        """
        self.row_user_indices = np.repeat(np.arange(self.nrow), self.ncol)[self.nodes]
        self.col_user_indices = np.tile(np.arange(self.ncol), reps=self.nrow)[
            self.nodes
        ]
        self.initialised = True

    def set_ptr(self, new_values: NDArray[Any]) -> None:
        """
        Sets the new values at the phreatic nodes

        Args:
            new_values (NDArray[Any]): new values at nodes selection
        """
        self.variable.variable_model[self.phreatic_modelid] = new_values

    def get_ptr(self) -> Any:
        """
        Gets the variable values at the phreatic nodes

        Returns:
            NDArray[Any]: Array with variable values at phreatic nodes of initial nodes selection
        """
        return self.variable.broadcast()[
            self.phreatic_layer_user_indices,
            self.row_user_indices,
            self.col_user_indices,
        ].flatten()  # type ignore

    @property
    def phreatic_layer_user_indices(self) -> Any:
        self._set_user_indices()
        return np.argmax(self.saturation.broadcast() > 0, axis=0).flatten()[self.nodes]

    @property
    def phreatic_modelid(self) -> Any:
        return self.variable.modelid.reshape((self.nlay, self.nrow, self.ncol))[
            self.phreatic_layer_user_indices,
            self.row_user_indices,
            self.col_user_indices,
        ].flatten()


class PhreaticBCArray(PhreaticModelArray):
    """
    This class sets the pointer arrays for the boundary condition-packages. In adition to the
    PhreaticModelArray-class it sets the package nodelist pointer to the corresponing Phreatic nodes.

    This class set and gets phreatic elements from the pointer arrays for model-packages.
    The initial nodelist gives the 'coupled' selection of nodes of the first model layer.
    Based on the node saturation, the coresponding underlying phreatic nodes are selected
    to get or set values.
    """

    initial_nodes: NDArray[Any]

    def __init__(
        self,
        shape: list[int],
        userid: NDArray[Any],
        ptr_saturation: NDArray[Any],
        ptr_package_variable: NDArray[Any],
        ptr_package_nodelist: NDArray[Any],
    ) -> None:
        super().__init__(
            shape, userid, ptr_saturation, ptr_package_variable, ptr_package_nodelist
        )
        self.variable = ExpandArray(
            shape,
            userid,
            ptr_package_variable,
            ptr_package_nodelist,
        )
        self.nodes_ptr = ptr_package_nodelist  # used for nodes after prepare_timestep

    def _set_user_indices(self) -> None:
        # the nodelist for bc-packages is only filled after the first prepare-timestep call
        # This method therefore is not called from the constructor
        if not self.initialised:
            self.nodes = self.nodes_ptr - 1
            userid = self.variable.userid
            self.row_user_indices = np.repeat(np.arange(self.nrow), self.ncol)[
                userid[self.nodes]
            ]
            self.col_user_indices = np.tile(np.arange(self.ncol), reps=self.nrow)[
                userid[self.nodes]
            ]
            self.initial_nodes = np.copy(self.nodes)
            self.initialised = True

    def set_ptr(self, new_values: NDArray[Any]) -> None:
        # The package nodelist is set to the phreatic nodes
        self.variable.variable_model[:] = new_values[:]
        self.variable.nodelist[:] = (self.phreatic_modelid + 1)[:]  # type ignore

    @property
    def phreatic_layer_user_indices(self) -> Any:
        self._set_user_indices()
        # use initial_nodes since self.nodes is updated by set_ptr method
        return np.argmax(self.saturation.broadcast() > 0, axis=0).flatten()[
            self.initial_nodes
        ]


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
        shape: list[int],
        userid: NDArray[Any],
        ptr_saturation: NDArray[Any],
        ptr_storage_sy: NDArray[Any],
        ptr_storage_ss: NDArray[Any],
        active_top_layer_nodes: NDArray[Any],
    ) -> None:
        self.zeros = np.zeros(active_top_layer_nodes.size)
        self.initial_sy = np.copy(ptr_storage_sy)
        self.initial_ss = np.copy(ptr_storage_ss)
        self.sy = PhreaticModelArray(
            shape,
            userid,
            ptr_saturation,
            ptr_storage_sy,
            active_top_layer_nodes,
        )
        self.ss = PhreaticModelArray(
            shape,
            userid,
            ptr_saturation,
            ptr_storage_ss,
            active_top_layer_nodes,
        )

    def reset(self) -> None:
        self.sy.variable.variable_model[:] = self.initial_sy[:]
        self.ss.variable.variable_model[:] = self.initial_ss[:]

    def set(self, new_sy: NDArray[Any], new_ss: NDArray[Any]) -> None:
        self.sy.set_ptr(new_sy)
        self.ss.set_ptr(self.zeros)


class PhreaticRecharge:
    """
    Wrapper class for RCH-package of MODFLOW 6. Contains methods for:

    - Setting recharge values and updating package-nodelist to current phreatic nodes
    """

    recharge: PhreaticBCArray

    def __init__(
        self,
        shape: list[int],
        userid: NDArray[Any],
        ptr_saturation: NDArray[Any],
        ptr_recharge: NDArray[Any],
        ptr_recharge_nodelist: NDArray[Any],
    ) -> None:
        self.recharge = PhreaticBCArray(
            shape, userid, ptr_saturation, ptr_recharge, ptr_recharge_nodelist
        )

    def set(self, new_recharge: NDArray[Any]) -> None:
        self.recharge.set_ptr(new_recharge)


class PhreaticHeads:
    """
    Wrapper class for heads of MODFLOW 6. Contains methods for:

    - Getting heads values for current phreatic nodes
    """

    heads: PhreaticModelArray

    def __init__(
        self,
        shape: list[int],
        userid: NDArray[Any],
        ptr_saturation: NDArray[Any],
        ptr_heads: NDArray[Any],
        active_top_layer_nodes: NDArray[Any],
    ) -> None:
        self.heads = PhreaticModelArray(
            shape, userid, ptr_saturation, ptr_heads, active_top_layer_nodes
        )

    def get(self) -> NDArray[Any]:
        return self.heads.get_ptr()
