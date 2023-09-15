from typing import Any, Dict

import numpy as np
from numpy import float_, int_
from numpy.typing import NDArray


class exchange_balance_2d:
    def __init__(self, dim: int) -> None:
        self.dim = dim

    def reset(self) -> None:
        """
        function initialses two water-balance dicts and sets arrays at 0.
        The dimension of the arrays is based on the shape of dflow 2d nodes
        """
        self.demand = {
            "msw-ponding2dflow2d_flux": np.zeros(shape=self.dim, dtype=np.float_),
            "msw-ponding2dflow2d_flux_positive": np.zeros(
                shape=self.dim, dtype=np.float_
            ),
            "msw-ponding2dflow2d_flux_negative": np.zeros(
                shape=self.dim, dtype=np.float_
            ),
        }
        self.realised = {
            "dflow2d-flux2msw-ponding_negative": np.zeros(
                shape=self.dim, dtype=np.float_
            ),
        }

    def compute_realised(self, sum_from_dflow: NDArray[np.float_]) -> None:
        sum_to_dflow = self.demand["msw-ponding2dflow2d_flux"]

        # compute shortage on negative elements only (infiltration demand from msw)
        demand_msw_negative = self.demand["msw-ponding2dflow2d_flux_negative"][:]
        mask = np.nonzero(demand_msw_negative)  # prevent zero division

        shortage_fraction = (
            sum_from_dflow[mask] - sum_to_dflow[mask]
        ) / demand_msw_negative[mask]
        shortage = demand_msw_negative[mask] * shortage_fraction

        # distribute shortage on negative contributions
        self.realised["dflow2d-flux2msw-ponding_negative"][mask] = (
            demand_msw_negative[mask] + shortage
        )
        pass


class exchange_balance_1d:
    def __init__(self, dim: int) -> None:
        self.dim = dim

    # TODO: maybe this class needs a check if sign of all values is as expected

    def reset(self) -> None:
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

    def set_realised_no_shortage(
        self, sum_from_dflow: NDArray[np.float_], sum_to_dflow: NDArray[np.float_]
    ) -> None:
        """
        This function sets the realised array elements on demand values for cases where no shortage is computed.
        There is no shortage at elements where the flux realised by dflow >= than the flux send to dflow.

        Parameters
        ----------
        sum_from_dflow : np.float_
            flux realised by dflow
        sum_to_dflow : np.float_
            flux send to dflow
        """
        condition = np.greater_equal(sum_to_dflow, sum_from_dflow)
        self.realised["dflow1d_flux2sprinkling_msw"][condition] = self.demand[
            "msw-sprinkling2dflow1d_flux"
        ][condition]
        self.realised["dflow1d_flux2mf-riv_negative"][condition] = self.demand[
            "mf-riv2dflow1d_flux_negative"
        ][condition]

    def set_realised_shortage_msw(
        self, sum_from_dflow: NDArray[np.float_], sum_to_dflow: NDArray[np.float_]
    ) -> None:
        """
        This function sets the realised array elements on demand or corrected values for cases where shortage is
        computed and shortage is smaller or equal tot the msw-demand. The realised values are:
        mf6: (-)realised = (-)demand
        msw: (-)realised = (-)realised + (+)shortage

        Parameters
        ----------
        sum_from_dflow : np.float_
            flux realised by dflow
        sum_to_dflow : np.float_
            flux send to dflow
        """
        shortage = np.absolute(sum_to_dflow - sum_from_dflow)
        demand_msw = self.demand["msw-sprinkling2dflow1d_flux"]
        condition = np.logical_and(
            shortage <= np.absolute(demand_msw),
            np.absolute(sum_to_dflow) > np.absolute(sum_from_dflow),
        )
        self.realised["dflow1d_flux2sprinkling_msw"][condition] = (
            demand_msw[condition] + shortage[condition]
        )
        self.realised["dflow1d_flux2mf-riv_negative"][condition] = self.demand[
            "mf-riv2dflow1d_flux_negative"
        ][condition]

    def set_realised_shortage_msw_mf6(
        self, sum_from_dflow: NDArray[np.float_], sum_to_dflow: NDArray[np.float_]
    ) -> None:
        """
        This function sets the realised array elements on zero or corrected values for cases where shortage is
        computed and shortage is larger than the msw-demand. The realised values are:
        mf6: (-)realised = (-)realised + ((+)shortage + (-)demand_msw)
        msw: (-)realised = 0

        Parameters
        ----------
        sum_from_dflow : np.float_
            flux realised by dflow
        sum_to_dflow : np.float_
            flux send to dflow
        """
        shortage = np.absolute(sum_to_dflow - sum_from_dflow)
        demand_msw = self.demand["msw-sprinkling2dflow1d_flux"]
        shortage_left = shortage + demand_msw
        demand_mf6_negative = self.demand["mf-riv2dflow1d_flux_negative"]
        condition = np.logical_and(
            shortage > np.absolute(demand_msw),
            np.absolute(sum_to_dflow) > np.absolute(sum_from_dflow),
        )
        self.realised["dflow1d_flux2sprinkling_msw"][condition] = 0
        self.realised["dflow1d_flux2mf-riv_negative"][condition] = (
            demand_mf6_negative[condition] + shortage_left[condition]
        )

    def check_maximum_shortage(
        self, sum_from_dflow: NDArray[np.float_], sum_to_dflow: NDArray[np.float_]
    ) -> None:
        """
        This function checks if the maximum shortage is not larger than the |negative contributions|.
        This should not occur and will result in erroneous fluxes.
        If it is the case, the function will throws an exception


        Parameters
        ----------
        sum_from_dflow : np.float_
            flux realised by dflow
        sum_to_dflow : np.float_
            flux send to dflow
        """
        id = 10
        shortage = np.around(np.absolute(sum_to_dflow - sum_from_dflow), decimals=id)
        demand = np.around(
            self.demand["msw-sprinkling2dflow1d_flux"]
            + self.demand["mf-riv2dflow1d_flux_negative"],
            decimals=id,
        )
        condition = np.logical_and(
            shortage > np.absolute(demand),
            np.less(sum_from_dflow.astype(np.float32), sum_to_dflow.astype(np.float32)),
        )
        if np.any(condition):
            raise ValueError("Computed shortage is larger than negative contributions")

    def compute_realised(self, sum_from_dflow: NDArray[np.float_]) -> None:
        """
        function calculates the realised flux based on the difference between the summend flux towards
        and returned from dflow. The realised fluxes are stored in the
        self.waterbalance_realised dict.

        Parameters
        ----------
        sum_dflow : NDArray[np.float]
           array with summed realised fluxes per dtsw-timstep by dflow
        """

        # initialize realised arrays for cases where all conditions are false due to rounding errors
        self.realised["dflow1d_flux2sprinkling_msw"] = self.demand[
            "msw-sprinkling2dflow1d_flux"
        ].copy()
        self.realised["dflow1d_flux2mf-riv_negative"] = self.demand[
            "mf-riv2dflow1d_flux_negative"
        ].copy()
        sum_to_dflow = self.demand["sum"][:]

        # update elements for no shortage
        self.set_realised_no_shortage(sum_from_dflow, sum_to_dflow)
        # update elements for cases with shortage + shortage <= msw_demand
        self.set_realised_shortage_msw(sum_from_dflow, sum_to_dflow)
        # update elements for cases with shortage + shortage > msw_demand
        self.set_realised_shortage_msw_mf6(sum_from_dflow, sum_to_dflow)
        # check if shortage is not larger than negative demand
        self.check_maximum_shortage(sum_from_dflow, sum_to_dflow)

        # (self.demand["mf-riv2dflow1d_flux_negative"] - self.realised["dflow1d_flux2mf-riv_negative"]) * 60*60*24
