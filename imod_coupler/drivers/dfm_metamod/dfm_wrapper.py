from ctypes import POINTER, byref, c_char_p, c_double, c_int, pointer
from typing import Optional

import numpy as np
from bmi.wrapper import BMIWrapper, create_string_buffer
from numpy.ctypeslib import as_array, ndpointer
from numpy.typing import NDArray


class DfmWrapper(BMIWrapper):  # type: ignore
    def get_number_1d_nodes(self) -> int:
        nr_nodes = self.get_var("ndxi")  # number of 1d cells
        nr_nodes2d = self.get_var("ndx2d")  # number of 2d cells
        return int(nr_nodes - nr_nodes2d)

    def get_waterlevels_1d(self) -> Optional[NDArray[np.float_]]:
        nr_nodes_1d = self.get_number_1d_nodes()
        if nr_nodes_1d == 0:
            return None
        all_waterlevels = self.get_var("s1")
        return np.asarray(all_waterlevels[-nr_nodes_1d:], dtype=np.float_)

    def get_cumulative_fluxes_1d_nodes(self) -> Optional[NDArray[np.float_]]:
        nr_nodes_1d = self.get_number_1d_nodes()
        if nr_nodes_1d == 0:
            return None
        all_cumulative_fluxes = self.get_var("vextcum")
        return np.asarray(all_cumulative_fluxes[-nr_nodes_1d:], dtype=np.float_)

    def get_snapped_flownode(
        self, input_node_x: NDArray[np.float64], input_node_y: NDArray[np.float64]
    ) -> NDArray[np.int_]:
        feature_type = create_string_buffer("flownode")
        assert len(input_node_x) == len(input_node_y)

        input_array_length = c_int(len(input_node_x))
        output_array_length = c_int()
        output_ptr_x = POINTER(c_double)()
        output_ptr_y = POINTER(c_double)()
        output_ptr_ids = POINTER(c_int)()
        ierror = c_int()
        self.library.get_snapped_feature(
            feature_type,
            byref(input_array_length),
            byref(input_node_x.ctypes.data_as(POINTER(c_double))),
            byref(input_node_y.ctypes.data_as(POINTER(c_double))),
            byref(output_array_length),
            byref(output_ptr_x),
            byref(output_ptr_y),
            byref(output_ptr_ids),
            byref(ierror),
        )

        if ierror.value != 0:
            raise RuntimeError("The `get_snapped_flownode` call failed.")

        output_ids = as_array(output_ptr_ids, shape=(output_array_length.value,))
        return output_ids
