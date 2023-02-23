from typing import Any, Dict

import numpy as np
from numpy import float_, int_
from numpy.typing import NDArray


class Exchange_balans:
    def __init__(self, dim: int) -> None:
        self
        self.dim = dim

    # check swapping signs
    def initialise(self) -> None:
        """
        function initialses the 2 water-balance dicts and sets all arrays at 0.
        The dimension of the arrays is based on the shape of dflow 1d nodes
        """
        self.demand = {
            "mf-riv2dflow1d_flux": np.zeros(shape=self.dim, dtype=np.float_),
            "mf-riv2dflow1d_passive_flux": np.zeros(shape=self.dim, dtype=np.float_),
            "mf-drn2dflow1d_flux": np.zeros(shape=self.dim, dtype=np.float_),
            "msw-ponding2dflow1d_flux": np.zeros(shape=self.dim, dtype=np.float_),
            "msw-sprinkling2dflow1d_flux": np.zeros(shape=self.dim, dtype=np.float_),
            "sum": np.zeros(shape=self.dim, dtype=np.float_),
        }
        self.realised = {
            "dflow1d_flux2sprinkling_msw": np.zeros(shape=self.dim, dtype=np.float_),
            "dflow1d_flux2mf-riv": np.empty(shape=self.dim, dtype=np.float_),
        }

    def sum_demand(self) -> None:
        """
        function calcualtes the sum of all arrays in self.water_balance_demand dict.
        The calculated flux is stored under the key "sum"
        """
        self.demand["sum"][:] = np.sum(list(self.demand.values())[:])

    def calculate_realised(self, sum_from_dflow: NDArray[np.float_]) -> None:
        """
        function calculates the realised flux based on the difference between the summend flux towards
        and returned from dflow. The realised fluxes are stored in the
        self.waterbalance_realised dict. In case of no shortage demand = realised:
        - 'dflow1d_flux2sprinkling_msw'-flux = 'msw-sprinkling2dflow1d_flux'
        - 'dflow1d_flux2mf-riv' = 'mf-riv2dflow1d_flux'

        Parameters
        ----------
        sum_dflow : NDArray[np.float]
           array as returnd by dflow after a run-cycle per dtsw-timstep
        """
        # riv_active: NDArray[np.float_]
        # riv_active_positive: NDArray[np.float_]
        # always_realised: NDArray[np.float_]
        # available: NDArray[np.float_]
        # sum_to_dflow: NDArray[np.float_]

        sum_to_dflow = self.demand["sum"][:]
        riv_active = self.demand["mf-riv2dflow1d_flux"][:]
        riv_active_positive = riv_active
        riv_active_positive[riv_active_positive < 0.0] = 0
        always_realised = (
            riv_active_positive[:]
            + self.demand["mf-riv2dflow1d_passive_flux"][:]
            + self.demand["mf-drn2dflow1d_flux"][:]
            + self.demand["msw-ponding2dflow1d_flux"][:]
        )
        available = sum_from_dflow[:] - always_realised[:]

        # no shortage
        # for msw: demand = realised
        # for mf6: demand = realised
        self.realised["dflow1d_flux2sprinkling_msw"][
            sum_from_dflow >= sum_to_dflow
        ] = self.demand["msw-sprinkling2dflow1d_flux"][sum_from_dflow >= sum_to_dflow]
        self.realised["dflow1d_flux2mf-riv"][
            sum_from_dflow >= sum_to_dflow
        ] = self.demand["mf-riv2dflow1d_flux"][sum_from_dflow >= sum_to_dflow]

        # only MODFLOW demand could be realised
        # for msw: demand = available - riv_active
        # for mf6: demand = realised
        left_available = available - riv_active
        self.realised["dflow1d_flux2sprinkling_msw"][
            (available >= riv_active) | (sum_from_dflow < sum_to_dflow)
        ] = left_available[(available >= riv_active) | (sum_from_dflow < sum_to_dflow)]
        self.realised["dflow1d_flux2mf-riv"][
            (available >= riv_active) | (sum_from_dflow < sum_to_dflow)
        ] = self.demand["mf-riv2dflow1d_flux"][
            (available >= riv_active) | (sum_from_dflow < sum_to_dflow)
        ]

        # Both MODFLOW and MetaSWAP demands can't be met
        # for msw: demand = 0
        # for mf6: return available
        self.realised["dflow1d_flux2sprinkling_msw"][
            (available < riv_active) | (sum_from_dflow < sum_to_dflow)
        ] = 0
        self.realised["dflow1d_flux2mf-riv"][
            (available < riv_active) | (sum_from_dflow < sum_to_dflow)
        ] = available[(available < riv_active) | (sum_from_dflow < sum_to_dflow)]