import numpy as np
from bmi.wrapper import BMIWrapper
from numpy.typing import NDArray


class ExtendedBMIWrapper(BMIWrapper):  # type: ignore
    def get_number_1d_nodes(self) -> int:
        nr_nodes = self.get_var("ndxi")  # number of 1d cells
        nr_nodes2d = self.get_var("ndx2d")  # number of 2d cells
        return int(nr_nodes - nr_nodes2d)

    def get_waterlevels_1d(self) -> NDArray[np.float_]:
        nr_nodes_1d = self.get_number_1d_nodes()
        if nr_nodes_1d == 0:
            return np.empty(shape=(0), dtype=np.float_)
        all_waterlevels = self.get_var("s1")
        return np.asarray(all_waterlevels[-nr_nodes_1d:], dtype=np.float_)

    def get_cumulative_fluxes_1d_nodes(self) -> NDArray[np.float_]:
        nr_nodes_1d = self.get_number_1d_nodes()
        if nr_nodes_1d == 0:
            return np.empty(shape=(0), dtype=np.float_)
        all_cumulative_fluxes = self.get_var("vextcum")
        return np.asarray(all_cumulative_fluxes[-nr_nodes_1d:], dtype=np.float_)
