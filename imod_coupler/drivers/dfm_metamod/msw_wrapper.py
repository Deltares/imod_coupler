from typing import Optional

import numpy as np
from numpy.typing import NDArray
from xmipy import XmiWrapper


class MswWrapper(XmiWrapper):
    def perform_surfacewater_timestep(self, idtsw: int) -> None:
        """
        function to start and excecute surface water timestep between msw and dflow

        Parameters
        ----------
        idtsw : integer*4
            index of time step within dtgw-cycle

        """
        iact = 1

        # call SIMGRO_DTSW(iact,idtsw)

    def finish_surfacewater_timestep(self, idtsw: float) -> None:
        """
        function to finish surface water timestep between msw and dflow

        Parameters
        ----------
        idtsw : integer*4
            index of time step within dtgw-cycle

        """
        iact = 2

        # call SIMGRO_DTSW(iact,idtsw)

    def get_surfacewater_sprinking_demand(self) -> NDArray[np.float_]:
        """returns the sprinkling volume demand from metaswap

        Parameters
        ----------
        none

        Returns
        -------
         NDArray[np.float_]:
            sprinkling demand of MetaSWAP in m3/dtgw. Array as a copy of the MetaSWAP intenal array,
            since the set function uses a different bmi/xmi-variable
        """
        sw_sprinkling_demand = self.get_value("dts2dfmputsp")
        return sw_sprinkling_demand

    def put_surfacewater_sprinking_demand(
        self, sprinking_demand: NDArray[np.float_]
    ) -> None:
        """sets the sprinkling volume demand in metaswap

        Parameters
        ----------
        sprinkiling_demand: NDArray[np.float_]:
            sprinkling demand of MetaSWAP in m3/dtgw

        Returns
        -------
        none

        """
        self.set_value("dts2dfmgetsp", sprinking_demand)

    def get_surfacewater_ponding_allocation(self) -> NDArray[np.float_]:
        """returns the ponding volume allocation from metaswap

        Parameters
        ----------
        none

        Returns
        -------
         NDArray[np.float_]:
            ponding volume allocation of MetaSWAP in m3/dtsw. Array as a copy of the MetaSWAP intenal array,
            since the set function uses a different bmi/xmi-variable
        """
        ponding_allocation = self.get_value("ts2dfmput")
        return ponding_allocation

    def put_surfacewater_ponding_allocation(
        self, ponding_allocation: NDArray[np.float_]
    ) -> None:
        """sets ponding volume allocation in metaswap

        Parameters
        ----------
        ponding_allocation: NDArray[np.float_]
            ponding volume allocation to set in metaswap in m3/dtsw

        Returns
        -------
        none
        """
        self.set_value("ts2dfmget", ponding_allocation)

    def put_ponding_level_1d(self, ponding_level_1d: NDArray[np.float_]) -> None:
        """sets ponding level from dlfow-1d in metaswap

        Parameters
        ----------
        ponding_level_1d: NDArray[np.float_]
            ponding level to set in metaswap in m relative to msw soil surface elevation (depth)

        Returns
        -------
        none
        """
        self.set_value("dfm2lvsw1Dk", ponding_level_1d)

    def put_ponding_level_2d(self, ponding_level_2d: NDArray[np.float_]) -> None:
        """sets ponding level from dlfow-2d in metaswap

        Parameters
        ----------
        ponding_level_2d: NDArray[np.float_]
            ponding level to set in metaswap in m relative to msw soil surface elevation (depth)

        Returns
        -------
        none
        """
        self.set_value("dfm2lvswk", ponding_level_2d)

    def get_svat_area(self) -> NDArray[np.float_]:
        """gets area's of svats in metaswap. This can ben used to calculate ponding volumes based on dlfow ponding levels

        Parameters
        ----------
        none

        Returns
        -------
         svat_area: NDArray[np.float_]
            area of svats (m2). Array as pointer to the MetaSWAP intenal array
        """
        svat_area = self.get_value_ptr("ark")
        return svat_area
