from typing import Any, Dict

import numpy as np
from numpy import float_, int_
from numpy.typing import NDArray


class Exchange_balans:
    def __init__(self, dim: int) -> None:
        self.dim = dim

    # TODO: maybe this class needs a check if sign of all values is as expected

    def initialise(self) -> None:
        """
        function initialses the 2 water-balance dicts and sets all arrays at 0.
        The dimension of the arrays is based on the shape of dflow 1d nodes
        """
        self.demand = {
            "mf-riv2dflow1d_flux": np.zeros(shape=self.dim, dtype=np.float_),
            "mf-riv2dflow1d_flux_positive": np.zeros(shape=self.dim, dtype=np.float_),
            "mf-riv2dflow1d_flux_negative": np.zeros(shape=self.dim, dtype=np.float_),
            "mf-riv2dflow1d_passive_flux": np.zeros(shape=self.dim, dtype=np.float_),
            "mf-drn2dflow1d_flux": np.zeros(shape=self.dim, dtype=np.float_),
            "msw-ponding2dflow1d_flux": np.zeros(shape=self.dim, dtype=np.float_),
            "msw-sprinkling2dflow1d_flux": np.zeros(shape=self.dim, dtype=np.float_),
            "sum": np.zeros(shape=self.dim, dtype=np.float_),
        }
        self.realised = {
            "dflow1d_flux2sprinkling_msw": np.zeros(shape=self.dim, dtype=np.float_),
            "dflow1d_flux2mf-riv_negative": np.zeros(shape=self.dim, dtype=np.float_),
        }

    def sum_demand(self) -> None:
        """
        function calculates the sum of all arrays in self.demand dict.
        The calculated flux is stored under the key "sum". This flux is used to send to dflow
        """
        sum_keys = [
            "mf-riv2dflow1d_flux",
            "mf-riv2dflow1d_passive_flux",
            "mf-drn2dflow1d_flux",
            "msw-ponding2dflow1d_flux",
            "msw-sprinkling2dflow1d_flux",
        ]
        sum_dict = {key: self.demand[key] for key in sum_keys}
        sum_array = np.stack(list(sum_dict.values()))
        self.demand["sum"][:] = sum_array.sum(axis=0)

    def compute_realised(self, sum_from_dflow: NDArray[np.float_]) -> None:
        """
        function calculates the realised flux based on the difference between the summend flux towards
        and returned from dflow. The realised fluxes are stored in the
        self.waterbalance_realised dict. In case of no shortage demand = realised:
        - 'dflow1d_flux2sprinkling_msw'-flux = 'msw-sprinkling2dflow1d_flux'
        - 'dflow1d_flux2mf-riv' = 'mf-riv2dflow1d_flux'
        In case of shortage, shortage will first be deducted to the msw-demand and after to mf6 demand.

        Parameters
        ----------
        sum_dflow : NDArray[np.float]
           array with summed realised fluxes per dtsw-timstep by dflow
        """

        sum_to_dflow = self.demand["sum"][:]
        # CASE 1: no shortage
        # for msw: realised = demand
        # for mf6: realised_negative = demand_negative
        condition = np.greater_equal(sum_from_dflow, sum_to_dflow)
        self.realised["dflow1d_flux2sprinkling_msw"][condition] = self.demand[
            "msw-sprinkling2dflow1d_flux"
        ][condition]
        self.realised["dflow1d_flux2mf-riv_negative"][condition] = self.demand[
            "mf-riv2dflow1d_flux_negative"
        ][condition]

        # shortage because of decreased waterlevels in dflow
        # CASE 2: only msw demand can't be met (shortage <= |msw_demand|)
        # for msw: realised = demand_msw + shortage
        # for mf6: realised_negative = demand_negative
        shortage = np.absolute(sum_to_dflow - sum_from_dflow)
        demand_msw = self.demand["msw-sprinkling2dflow1d_flux"]
        condition = np.logical_and(
            shortage <= np.absolute(demand_msw), (sum_from_dflow < sum_to_dflow)
        )
        self.realised["dflow1d_flux2sprinkling_msw"][condition] = (
            demand_msw[condition] + shortage[condition]
        )
        self.realised["dflow1d_flux2mf-riv_negative"][condition] = self.demand[
            "mf-riv2dflow1d_flux_negative"
        ][condition]

        # CASE 3: both mf6 and msw demands cant be met (shortage > |msw_demand|)
        # for msw: realised = 0
        # for mf6: realised_negative = demand_mf6_negative + shortage_left (shortage_left = shortage - demand_msw))
        shortage_left = shortage + demand_msw
        demand_mf6_negative = self.demand["mf-riv2dflow1d_flux_negative"]
        condition = np.logical_and(
            shortage > np.absolute(demand_msw), sum_from_dflow < sum_to_dflow
        )

        self.realised["dflow1d_flux2sprinkling_msw"][condition] = 0
        self.realised["dflow1d_flux2mf-riv_negative"][condition] = (
            demand_mf6_negative[condition] + shortage_left[condition]
        )

        # aditional check for cases where sum_from_dflow < sum_to_dflow
        # the maximum shortage can't be larger than the | negative contributions |
        # This should not occur and will result in erroneous fluxes
        condition = np.logical_and(
            shortage > np.absolute(demand_msw + demand_mf6_negative),
            sum_from_dflow < sum_to_dflow,
        )
        if np.any(condition):
            raise ValueError("Computed shortage is larger than negative contributions")
