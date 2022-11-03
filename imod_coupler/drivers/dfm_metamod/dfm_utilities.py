from bmi.wrapper import BMIWrapper
import numpy as np


class DfmUtilities:
    @classmethod
    def get_number_1d_nodes(cls, dflow: BMIWrapper):
        nr_nodes = dflow.get_var("ndxi")  # number of 1d cells
        nr_nodes2d = dflow.get_var("ndx2d")  # number of 2d cells
        return nr_nodes - nr_nodes2d

    @classmethod
    def get_waterlevels_1d(cls, dflow: BMIWrapper):
        nr_nodes_1d = cls.get_number_1d_nodes(dflow)
        all_waterlevels = dflow.get_var("s1")
        return all_waterlevels[-nr_nodes_1d:]

    @classmethod
    def get_waterlevels_1d(cls, dflow: BMIWrapper):
        nr_nodes_1d = cls.get_number_1d_nodes(dflow)
        all_waterlevels = dflow.get_var("s1")
        return all_waterlevels[-nr_nodes_1d:]

    @classmethod
    def get_cumulative_fluxes_1d_nodes(cls, dflow: BMIWrapper):
        nr_nodes_1d = cls.get_number_1d_nodes(dflow)
        all_cumulative_fluxes = dflow.get_var("vextcum")
        return all_cumulative_fluxes[-nr_nodes_1d:]
