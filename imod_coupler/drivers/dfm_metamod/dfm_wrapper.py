from ctypes import POINTER, byref, c_char_p, c_double, c_int, pointer
from typing import Optional

import numpy as np
from bmi.wrapper import BMIWrapper, create_string_buffer
from numpy.ctypeslib import as_array, ndpointer
from numpy.typing import NDArray


class DfmWrapper(BMIWrapper):  # type: ignore
    def get_number_nodes(self) -> int:
        """
        Returns
        -------
        int
            the number of nodes in the dflow-FM model
        """

        nr_nodes = self.get_var("ndxi")  # number of cells
        return int(nr_nodes)

    def get_number_1d_nodes(self) -> int:
        """
        Returns
        -------
        int
            the number of 1d nodes in the dflow-FM model
        """

        return self.get_number_nodes() - self.get_number_2d_nodes()

    def get_number_2d_nodes(self) -> int:
        """
        Returns
        -------
        int
            the number of 2d nodes in the dflow-FM model
        """

        nr_nodes2d = self.get_var("ndx2d")  # number of 2d cells
        return int(nr_nodes2d)

    def get_waterlevels_1d(self) -> NDArray[np.float_]:
        """
        Returns
        -------
        Optional[NDArray[np.float_]]
            an array with the waterlevels of the 1d nodes in the dflow-FM model,
            or None if there ar no 1d nodes.
        """

        nr_nodes_1d = self.get_number_1d_nodes()
        nr_nodes_2d = self.get_number_2d_nodes()
        if nr_nodes_1d == 0:
            raise ValueError("No dflow 1d nodes found!")
        all_waterlevels = self.get_var("s1")
        return np.asarray(
            all_waterlevels[nr_nodes_2d : nr_nodes_2d + nr_nodes_1d], dtype=np.float_
        )

    def get_waterlevels_2d(self) -> NDArray[np.float_]:
        """
        Returns
        -------
        Optional[NDArray[np.float_]]
            an array with the waterlevels of the 2d nodes in the dflow-FM model,
            or None if there ar no 2d nodes.
        """

        nr_nodes_2d = self.get_number_2d_nodes()
        if nr_nodes_2d == 0:
            raise ValueError("No dflow 1d nodes found!")
        all_waterlevels = self.get_var("s1")
        return np.asarray(all_waterlevels[:nr_nodes_2d], dtype=np.float_)

    def get_bed_level_2d(self) -> NDArray[np.float_]:
        """
        Returns
        -------
        Optional[NDArray[np.float_]]
            an array with the waterlevels of the 2d nodes in the dflow-FM model,
            or None if there ar no 2d nodes.
        """

        nr_nodes_2d = self.get_number_2d_nodes()
        if nr_nodes_2d == 0:
            raise ValueError("No dflow 1d nodes found!")
        all_bed_levels = self.get_var("bl")
        return np.asarray(all_bed_levels[:nr_nodes_2d], dtype=np.float_)

    def get_cumulative_fluxes_1d_nodes(self) -> NDArray[np.float_]:
        """
        Returns
        -------
        Optional[NDArray[np.float_]]
            an array with the cumulative fluxes of the 1d nodes in the dflow-FM model,
            or None if there ar no 1d nodes.
        """
        nr_nodes_1d = self.get_number_1d_nodes()
        if nr_nodes_1d == 0:
            raise ValueError("No dflow 1d nodes found!")
        all_cumulative_fluxes = self.get_var("vextcum")
        return np.asarray(all_cumulative_fluxes[-nr_nodes_1d:], dtype=np.float_)

    def get_cumulative_fluxes_2d_nodes(self) -> NDArray[np.float_]:
        """
        Returns
        -------
        Optional[NDArray[np.float_]]
            an array with the cumulative fluxes of the 2d nodes in the dflow-FM model,
            or None if there ar no 1d nodes.
        """
        nr_nodes_2d = self.get_number_2d_nodes()
        if nr_nodes_2d == 0:
            raise ValueError("No dflow 1d nodes found!")
        all_cumulative_fluxes = self.get_var("vextcum")
        return np.asarray(all_cumulative_fluxes[:nr_nodes_2d], dtype=np.float_)

    def set_1d_river_fluxes(self, river_flux: NDArray[np.float_]) -> None:
        """
        Sets the DFLOW-FM array qext (external fluxes) for the 1d nodes

        Parameters
        ----------
        river_flux : NDArray[np.float_]
            the 1d river fluxes that need to be set to the DFLOW-FM array "qext"

        Raises
        ------
        ValueError
            mismatch between expected size and actual size.
        """

        nr_nodes_2d = self.get_var("ndx2d")  # number of 2d cells
        nr_nodes_1d = self.get_number_1d_nodes()
        if len(river_flux) != nr_nodes_1d:
            raise ValueError(
                f"Expected number of river fluxes: {nr_nodes_1d}, got {len(river_flux)}"
            )
        self.set_var_slice("qext", [nr_nodes_2d], [nr_nodes_1d], river_flux)

    def set_2d_fluxes(self, river_flux: NDArray[np.float_]) -> None:
        """
        Sets the DFLOW-FM array qext (external fluxes) for the 2d nodes

        Parameters
        ----------
        river_flux : NDArray[np.float_]
            the 2d fluxes that need to be set to the DFLOW-FM array "qext"

        Raises
        ------
        ValueError
            mismatch between expected size and actual size.
        """

        nr_nodes_2d = self.get_var("ndx2d")  # number of 2d cells
        if len(river_flux) != nr_nodes_2d:
            raise ValueError(
                f"Expected number of river fluxes: {nr_nodes_2d}, got {len(river_flux)}"
            )
        self.set_var_slice("qext", [0], [nr_nodes_2d], river_flux)

    def get_1d_river_fluxes(self) -> NDArray[np.float_]:
        """
        Returns
        -------
        Optional[NDArray[np.float_]]
            the DFLOW_FM external fluxes ( "qext") for the 1d nodes
        """
        nr_nodes_1d = self.get_number_1d_nodes()
        if nr_nodes_1d == 0:
            raise ValueError("No dflow 1d nodes found!")
        q_ext = self.get_var("qext")
        return np.asarray(q_ext[-nr_nodes_1d:], dtype=np.float_)

    def get_2d_fluxes(self) -> NDArray[np.float_]:
        """
        Returns
        -------
        Optional[NDArray[np.float_]]
            the DFLOW_FM external fluxes ( "qext") for the 1d nodes
        """
        nr_nodes_2d = self.get_number_2d_nodes()
        if nr_nodes_2d == 0:
            raise ValueError("No dflow 2d nodes found!")
        q_ext = self.get_var("qext")
        return np.asarray(q_ext[:nr_nodes_2d], dtype=np.float_)

    def get_snapped_flownode(
        self, input_node_x: NDArray[np.float64], input_node_y: NDArray[np.float64]
    ) -> NDArray[np.int_]:
        """Calculates the flownodes near the given x-y coordinates

        Parameters
        ----------
        input_node_x : NDArray[np.float64]
            x-coordinates of the input nodes
        input_node_y : NDArray[np.float64]
            y-coordinates of the input nodes

        Returns
        -------
        NDArray[np.int_]
            flownodes near the given x-y coordinates
        """
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

    def get_current_time_days(self) -> float:
        return (float)(super().get_current_time() / 86400.0)
