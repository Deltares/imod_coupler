from typing import Optional

import numpy as np
from bmi.wrapper import BMIWrapper
from numpy.typing import NDArray


class DfmWrapper(BMIWrapper):  # type: ignore
    def get_number_1d_nodes(self) -> int:
        """
        Returns the number of 1d nodes in the dflow-FM model
        """
        nr_nodes = self.get_var("ndxi")  # number of cells
        nr_nodes2d = self.get_var("ndx2d")  # number of 2d cells
        return int(nr_nodes - nr_nodes2d)

    def get_waterlevels_1d(self) -> Optional[NDArray[np.float_]]:
        """
        Returns the waterlevels of the 1d nodes in the dflow-FM model
        """
        nr_nodes_1d = self.get_number_1d_nodes()
        if nr_nodes_1d == 0:
            return None
        all_waterlevels = self.get_var("s1")
        return np.asarray(all_waterlevels[-nr_nodes_1d:], dtype=np.float_)

    def get_cumulative_fluxes_1d_nodes(self) -> Optional[NDArray[np.float_]]:
        """
        Returns the cumulative fluxes of the 1d nodes in the dflow-FM model
        """
        nr_nodes_1d = self.get_number_1d_nodes()
        if nr_nodes_1d == 0:
            return None
        all_cumulative_fluxes = self.get_var("vextcum")
        return np.asarray(all_cumulative_fluxes[-nr_nodes_1d:], dtype=np.float_)

    def set_1d_river_fluxes(self, river_flux: NDArray[np.float_]) -> None:
        """
        sets the elements of the DFLOW-FM array "qext" that correspond to 1d nodes to
        the river_flux
        """
        nr_nodes_2d = self.get_var("ndx2d")  # number of 2d cells
        nr_nodes_1d = self.get_number_1d_nodes()
        if len(river_flux) != nr_nodes_1d:
            raise ValueError(f"Expected number of river fluxes: {nr_nodes_1d}")
        self.set_var_slice("qext", river_flux, nr_nodes_2d, nr_nodes_1d)

    def get_1d_river_fluxes(self, river_flux: NDArray[np.float_]) -> NDArray[np.float_]:
        """
        assigns external fluxes
        """
        nr_nodes_1d = self.get_number_1d_nodes()
        if len(river_flux) != nr_nodes_1d:
            raise ValueError(f"Expected number of river fluxes: {nr_nodes_1d}")
        q_ext = self.get_var("qext")
        q_ext_1dnodes = q_ext[-nr_nodes_1d:]
        return q_ext_1dnodes
