from typing import Optional

import numpy as np
from numpy.typing import NDArray
from xmipy import XmiWrapper


class MswWrapper(XmiWrapper):
    def perform_surfacewater_timestep(self, idtsw: float) -> None:
        """
        function to start and excecute surface water timestep between msw and dflow

        Parameters
        ----------
        idtsw : float
            timesetp duration as fraction relative to the MF6 timestep durations (days)

        """
        iact = 1

        # call SIMGRO_DTSW(iact,idtsw)

    def finish_surfacewater_timestep(self, idtsw: float) -> None:
        """
        function to finish surface water timestep between msw and dflow

        Parameters
        ----------
        idtsw : float
            timesetp duration as fraction relative to the MF6 timestep durations (days)

        """
        iact = 2

        # call SIMGRO_DTSW(iact,idtsw)

    def get_sw_sprinking_demand(self) -> NDArray[np.float_]:
        """returns the sprinkling volume demand from metaswap

        Parameters
        ----------
        none

        Returns
        -------
         NDArray[np.float_]:
            sprinkling demand of MetaSWAP in m3/dtgw
        """
        sw_sprinkling_demand = self.get_value_ptr("dcupsswdemm3i")
        return sw_sprinkling_demand

    def get_ponding_allocation(self) -> NDArray[np.float_]:
        """returns the ponding volume allocation from metaswap

        Parameters
        ----------
        none

        Returns
        -------
         NDArray[np.float_]:
            ponding volume allocation of MetaSWAP in m3/dtsw?
        """
        ponding_allocation = self.get_value_ptr("ts2dfmget")
        return ponding_allocation

    def put_ponding_allocation(self, ponding_allocation) -> None:
        """sets ponding volume allocation in metaswap

        Parameters
        ----------
        ponding_allocation: NDArray[np.float_]
            ponding volume allocation to set in metaswap

        Returns
        -------
        none
        """
        self.get_value_ptr("ts2dfmput", ponding_allocation)

    # MetaSWAP_performSurfacewaterTimestep(idtsw)
