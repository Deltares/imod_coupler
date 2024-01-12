from typing import Any, Dict

import numpy as np
from numpy import float_
from numpy.typing import NDArray
from ribasim_api import RibasimApi


class exchange_balance_1d:
    predicted: dict[str, NDArray[np.float_]]
    realised: dict[str, NDArray[np.float_]]
    dim: int
    sum_keys: list[str]

    def __init__(self, dim: int) -> None:
        self.dim = dim
        self.sum_keys = []
        self.predicted = {
            "sum": np.zeros(shape=self.dim, dtype=np.float_),
        }
        self.realised = {
            "sum": np.zeros(shape=self.dim, dtype=np.float_),
        }

    def reset(self) -> None:
        """
        function initialses the 2 water-balance dicts and sets all arrays at 0.
        The dimension of the arrays is based on the shape of dflow 1d nodes
        """
        self.predicted = {
            "msw_ponding2riba_flux": np.zeros(shape=self.dim, dtype=np.float_),
            "msw_sprinkling2riba_flux": np.zeros(shape=self.dim, dtype=np.float_),
            "sum": np.zeros(shape=self.dim, dtype=np.float_),
        }
        for val in self.predicted.values():
            val[:] = np.zeros(shape=self.dim, dtype=np.float_)

        for val in self.realised.values():
            val[:] = np.zeros(shape=self.dim, dtype=np.float_)

    def sum_predicted(self) -> None:
        """
        function calculates the sum of all arrays in self.predicted dict.
        The calculated flux is stored under the key "sum". This flux is used to send to ribasim
        """
        sum_dict = {key: self.predicted[key] for key in self.sum_keys}
        sum_array = np.stack(list(sum_dict.values()))
        self.predicted["sum"][:] = sum_array.sum(axis=0)

    def set_realised_no_shortage(
        self, sum_from_sw: NDArray[np.float_], sum_to_sw: NDArray[np.float_]
    ) -> None:
        """
        This function sets the realised array elements on predicted values for cases where no shortage is computed.
        There is no shortage at elements where the flux realised by the surface water component >= than the flux send to the surface water component.

        Parameters
        ----------
        sum_from_sw : np.float_
            flux realised by the surface water component
        sum_to_sw : np.float_
            flux send to the surface water component
        """
        condition = np.greater_equal(sum_to_sw, sum_from_sw)
        for key in self.predicted.keys():
            if key in self.realised:
                self.realised[key][condition] = self.predicted[key][condition]


class exchange_ribasim_1d(exchange_balance_1d):
    ribasim_infiltration: NDArray[Any]
    ribasim_drainage: NDArray[Any]

    def __init__(self, ribasim: RibasimApi) -> None:
        self.riba = ribasim
        self.ribasim_drainage = self.riba.get_value_ptr("drainage")
        self.ribasim_infiltration = self.riba.get_value_ptr("infiltration")
        self.ribasim_level = self.riba.get_value_ptr("level")
        exchange_balance_1d.__init__(self, np.size(self.ribasim_drainage))
        self.predicted["msw_ponding2riba_flux"] = np.zeros(
            shape=self.dim, dtype=np.float_
        )
        self.realised["msw_ponding2riba_flux"] = np.zeros(
            shape=self.dim, dtype=np.float_
        )

    def to_ribasim(self) -> None:
        if self.ribasim_drainage is not None and self.ribasim_drainage is not None:
            self.ribasim_drainage[:] = np.where(
                self.predicted["sum"][:] > 0, self.predicted["sum"][:], 0.0
            )
            self.ribasim_infiltration[:] = np.where(
                self.predicted["sum"][:] < 0, self.predicted["sum"][:], 0.0
            )

    def sum_predicted(self) -> None:
        self.sum_keys = [
            "msw_ponding2riba_flux",
            "msw_sprinkling2riba_flux",
        ]
        super().sum_predicted()
