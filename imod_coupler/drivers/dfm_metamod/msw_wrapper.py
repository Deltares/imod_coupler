from ctypes import byref, c_int
from pathlib import Path
from typing import Any, Optional, Union

import numpy as np
from numpy.typing import NDArray
from xmipy import XmiWrapper


class MswWrapper(XmiWrapper):
    def __init__(
        self,
        lib_path: Union[str, Path],
        lib_dependency: Union[str, Path, None] = None,
        working_directory: Union[str, Path, None] = None,
        timing: bool = False,
    ):
        super().__init__(lib_path, lib_dependency, working_directory, timing)

    def initialize_surface_water_component(self) -> None:
        self._execute_function(self.lib.init_sw_component)

    def perform_sw_time_step(self, idtsw: int) -> None:
        idtsw_c = c_int(idtsw)
        self._execute_function(self.lib.perform_sw_time_step, byref(idtsw_c))

    def finish_surface_water_time_step(self, idtsw: int) -> None:
        idtsw_c = c_int(idtsw)
        self._execute_function(self.lib.finish_sw_time_step, byref(idtsw_c))

    def get_sw_time_step(self) -> float:
        """returns the time step length for fast (surfacewater) processes from metaswap

        Parameters
        ----------
        none

        Returns
        -------
         NDArray[np.float_]:
            surface water timestep length in days
        """
        dtsw = self.get_value("dtsw")
        return float(dtsw[0])

    def get_surfacewater_sprinking_demand_ptr(self) -> NDArray[np.float_]:
        """returns the sprinkling volume demand from metaswap

        Parameters
        ----------
        none

        Returns
        -------
         NDArray[np.float_]:
            sprinkling demand of MetaSWAP in m3/ dtgw. Array as pointer of the MetaSWAP intenal array.
            Internally MetaSWAP uses a different array for get and set operations.
        """
        return self.get_value_ptr("ts2dfmputsp")

    def get_surfacewater_sprinking_realised_ptr(self) -> NDArray[np.float_]:
        """sets the sprinkling volume demand in metaswap.

        Parameters
        ----------
        sprinkiling_demand: NDArray[np.float_]:
            sprinkling demand of MetaSWAP in m3/dtgw

        Returns
        -------
        none

        """
        return self.get_value_ptr("dfm2tsgetsp")

    def get_surfacewater_ponding_allocation_ptr(self) -> NDArray[np.float_]:
        """retruns the pointer to the ponding volume allocation array in MetaSWAP.
        MetaSWAP uses two different ponding volume arrays. One for ponding allocation at the beginning of a (sub) timestep
        and one for the returned realised volume at the end of the (sub) timestep.

        Parameters
        ----------
        none

        Returns
        -------
         NDArray[np.float_]:
            ponding volume allocation of MetaSWAP in m3/dtsw. Array as pointer of the MetaSWAP intenal array.
            Internally MetaSWAP uses a different array for get and set operations.
        """
        return self.get_value_ptr("ts2dfmput")

    def get_surfacewater_ponding_realised_ptr(self) -> NDArray[np.float_]:
        """retruns the pointer to the ponding volume realised array in metaSWAP
        MetaSWAP uses two different ponding volume arrays. One for ponding allocation at the beginning of a (sub) timestep
        and one for the returned realised volume at the end of the (sub) timestep.

        Parameters
        ----------
        none

        Returns
        -------
        none
        """
        return self.get_value_ptr("ts2dfmget")

    def get_ponding_level_2d_ptr(self) -> NDArray[np.float_]:
        """get ponding level from dlfow-2d in metaswap

        Parameters
        ----------
        none

        Returns
        -------
        ponding_level_2d: NDArray[np.float_]
            ponding level 2d
        """

        return self.get_value_ptr("dfm2lvswk")

    def get_svat_area_ptr(self) -> NDArray[np.float_]:
        """gets area's of svats in metaswap. This can ben used to calculate ponding volumes based on dlfow ponding levels

        Parameters
        ----------
        none

        Returns
        -------
         svat_area: NDArray[np.float_]
            area of svats (m2). Array as pointer to the MetaSWAP intenal array
        """
        return self.get_value_ptr("ark")

    def get_head_ptr(self) -> NDArray[np.float_]:
        """gets heads array from metaswap

        Parameters
        ----------
        none

        Returns
        -------
         msw_head: NDArray[np.float_]
            array of the heads used by metaswap. Array as pointer to the MetaSWAP intenal array
        """
        return self.get_value_ptr("dhgwmod")

    def get_volume_ptr(self) -> NDArray[np.float_]:
        """gets volume array from metaswap

        Parameters
        ----------
        none

        Returns
        -------
         msw_volume: NDArray[np.float_]
            array of volume used by metaswap. Array as pointer to the MetaSWAP intenal array
        """
        return self.get_value_ptr("dvsim")

    def get_storage_ptr(self) -> NDArray[np.float_]:
        """gets storage array from metaswap

        Parameters
        ----------
        none

        Returns
        -------
         msw_storage: NDArray[np.float_]
            array of storage used by metaswap. Array as pointer to the MetaSWAP intenal array
        """
        return self.get_value_ptr("dsc1sim")
