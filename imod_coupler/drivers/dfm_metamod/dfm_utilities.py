import numpy as np
from bmi.wrapper import BMIWrapper


class DfmUtilities:
    @classmethod
    def get_number_1d_nodes(cls, dflow: BMIWrapper) -> int:
        nr_nodes = dflow.get_var("ndxi")  # number of 1d cells
        nr_nodes2d = dflow.get_var("ndx2d")  # number of 2d cells
        return int(nr_nodes - nr_nodes2d)

    @classmethod
    def get_waterlevels_1d(cls, dflow: BMIWrapper) -> np.ndarray[float]:
        nr_nodes_1d = cls.get_number_1d_nodes(dflow)
        if nr_nodes_1d == 0:
            return np.empty(shape=(0), dtype=np.float_)
        all_waterlevels = dflow.get_var("s1")
        return np.asarray(all_waterlevels[-nr_nodes_1d:], dtype=np.float_)

    @classmethod
    def get_cumulative_fluxes_1d_nodes(cls, dflow: BMIWrapper) -> np.ndarray[float]:
        nr_nodes_1d = cls.get_number_1d_nodes(dflow)
        if nr_nodes_1d == 0:
            return np.empty(shape=(0), dtype=np.float_)
        all_cumulative_fluxes = dflow.get_var("vextcum")
        return np.asarray(all_cumulative_fluxes[-nr_nodes_1d:], dtype=np.float_)
