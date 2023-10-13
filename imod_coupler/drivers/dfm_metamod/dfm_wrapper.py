from ctypes import POINTER, byref, c_char_p, c_double, c_int, c_void_p, pointer
from typing import Optional

import numpy as np
from bmi.wrapper import BMIWrapper, create_string_buffer
from numpy.ctypeslib import as_array, ndpointer
from numpy.typing import NDArray
from scipy.spatial import KDTree


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

    def get_waterlevels_1d_ptr(self) -> NDArray[np.float_]:
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

    def get_bedlevels_1d_ptr(self) -> NDArray[np.float_]:
        """
        Returns
        -------
        Optional[NDArray[np.float_]]
            an array with the bedlevels of the 1d nodes in the dflow-FM model,
            or None if there ar no 1d nodes.
        """

        nr_nodes_1d = self.get_number_1d_nodes()
        nr_nodes_2d = self.get_number_2d_nodes()
        if nr_nodes_1d == 0:
            raise ValueError("No dflow 1d nodes found!")
        all_bedlevels = self.get_var("bl")
        return np.asarray(
            all_bedlevels[nr_nodes_2d : nr_nodes_2d + nr_nodes_1d], dtype=np.float_
        )

    def __get_internal_node_coordinates__(self) -> NDArray[np.double]:
        """
        Returns
        -------
        Optional[NDArray[np.float_]]
            an array with the x-coordinates of all internal nodes
        Optional[NDArray[np.float_]]
            an array with the y-coordinates of all internal nodes
        """

        nr_nodes_1d = self.get_number_1d_nodes()
        nr_nodes_2d = self.get_number_2d_nodes()
        xz = self.get_var("xz")
        npxz = np.asarray(xz[: nr_nodes_2d + nr_nodes_1d], dtype=np.double)
        yz = self.get_var("yz")
        npyz = np.asarray(yz[: nr_nodes_2d + nr_nodes_1d], dtype=np.double)
        return np.array(np.c_[npxz, npyz])

    def get_waterlevels_2d_ptr(self) -> NDArray[np.float_]:
        """
        Returns
        -------
        Optional[NDArray[np.float_]]
            an array with the waterlevels of the 2d nodes in the dflow-FM model,
            or None if there ar no 2d nodes.
        """

        nr_nodes_2d = self.get_number_2d_nodes()
        all_waterlevels = self.get_var("s1")
        return np.asarray(all_waterlevels[:nr_nodes_2d], dtype=np.float_)

    def get_bed_level_2d_ptr(self) -> NDArray[np.float_]:
        """
        Returns
        -------
        Optional[NDArray[np.float_]]
            an array with the waterlevels of the 2d nodes in the dflow-FM model,
            or None if there ar no 2d nodes.
        """

        nr_nodes_2d = self.get_number_2d_nodes()
        all_bed_levels = self.get_var("bl")
        return np.asarray(all_bed_levels[:nr_nodes_2d], dtype=np.float_)

    def get_cumulative_fluxes_1d_nodes_ptr(self) -> NDArray[np.float_]:
        """
        Returns
        -------
        Optional[NDArray[np.float_]]
            an array with the cumulative fluxes of the 1d nodes in the dflow-FM model,
            or None if there ar no 1d nodes.
        """
        nr_nodes_1d = self.get_number_1d_nodes()
        nr_nodes_2d = self.get_number_2d_nodes()
        if nr_nodes_1d == 0:
            raise ValueError("No dflow 1d nodes found!")
        all_cumulative_fluxes = self.get_var("vextcum")
        return np.asarray(
            all_cumulative_fluxes[nr_nodes_2d : nr_nodes_1d + nr_nodes_2d],
            dtype=np.float_,
        )

    def get_cumulative_fluxes_2d_nodes_ptr(self) -> NDArray[np.float_]:
        """
        Returns
        -------
        Optional[NDArray[np.float_]]
            an array with the cumulative fluxes of the 2d nodes in the dflow-FM model,
            or None if there ar no 1d nodes.
        """
        nr_nodes_2d = self.get_number_2d_nodes()
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

        nr_nodes_1d = self.get_number_1d_nodes()
        if len(river_flux) != nr_nodes_1d:
            raise ValueError(
                f"Expected number of river fluxes: {nr_nodes_1d}, got {len(river_flux)}"
            )
        dfm_river_flux = self.get_1d_river_fluxes_ptr()
        if dfm_river_flux is not None:
            dfm_river_flux[:] = river_flux[:]

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
        dfm_river_flux = self.get_2d_river_fluxes_ptr()
        if dfm_river_flux is not None:
            dfm_river_flux[:] = river_flux[:]

    def get_1d_river_fluxes_ptr(self) -> NDArray[np.float_]:
        """
        Returns
        -------
        Optional[NDArray[np.float_]]
            the DFLOW_FM external fluxes ( "qext") for the 1d nodes
        """
        nr_nodes_1d = self.get_number_1d_nodes()
        nr_nodes_2d = self.get_number_2d_nodes()
        if nr_nodes_1d == 0:
            raise ValueError("No dflow 1d nodes found!")
        q_ext = self.get_var("qext")
        return np.asarray(
            q_ext[nr_nodes_2d : nr_nodes_1d + nr_nodes_2d], dtype=np.float_
        )

    def get_2d_river_fluxes_ptr(self) -> NDArray[np.float_]:
        """
        Returns
        -------
        Optional[NDArray[np.float_]]
            the DFLOW_FM external fluxes ( "qext") for the 2d nodes
        """
        nr_nodes_2d = self.get_number_2d_nodes()
        if nr_nodes_2d == 0:
            raise ValueError("No dflow 2d nodes found!")
        q_ext = self.get_var("qext")
        return np.asarray(q_ext[:nr_nodes_2d], dtype=np.float_)

    def init_kdtree(self) -> None:
        nx1d = self.get_number_1d_nodes()
        nx2d = self.get_number_2d_nodes()
        flowelem_xy = self.__get_internal_node_coordinates__()
        self.kdtree1D = KDTree(flowelem_xy[nx2d : nx2d + nx1d])
        self.kdtree2D = KDTree(flowelem_xy[:nx2d])

    def get_2d_fluxes_ptr(self) -> NDArray[np.float_]:
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
        self,
        input_node_x: NDArray[np.float64],
        input_node_y: NDArray[np.float64],
        indtp: str,
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

        if indtp == "1D":
            feature_type = create_string_buffer("flownode1d")
        elif indtp == "2D":
            feature_type = create_string_buffer("flownode2d")
        else:
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
        if indtp == "1D":
            return output_ids
        else:
            nx2d = self.get_number_2d_nodes()
            return output_ids - nx2d

    def get_current_time_days(self) -> float:
        return (float)(super().get_current_time() / 86400.0)
