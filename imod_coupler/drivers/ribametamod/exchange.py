from typing import Any

import numpy as np
from numpy.typing import NDArray
from ribasim_api import RibasimApi


class exchange_balance:
    demands: dict[str, NDArray[np.float_]]
    demands_negative: dict[str, NDArray[np.float_]]
    realised_negative: dict[str, NDArray[np.float_]]
    shape: int
    sum_keys: list[str]

    def __init__(self, shape: int, labels: list[str]) -> None:
        self.shape = shape
        self.flux_labels = labels
        self._init_arrays()

    def set_realised(
        self, realised: NDArray[np.float_]
    ) -> None:
        """
        This function computes the realised volumes
        """
        shortage = np.absolute(self.demand - realised)
        demand_negative = self.demand_negative
        self._check_valid_shortage(shortage, demand_negative)
        realised_fraction = self._zeros_array
        zero_devision_mask = demand_negative != 0.0
        realised_fraction = 1 - (- shortage / demand_negative)
        for flux_label in self.flux_labels:
            self.realised_negative[flux_label][zero_devision_mask] = (self.demands_negative[flux_label] * realised_fraction)[zero_devision_mask]
    
    def reset(self) -> None:
        """
        function sets all arrays to zero
        """
        for flux_label in self.flux_labels:
            self.demands[flux_label][:] = 0.0
            self.demands_negative[flux_label][:] = 0.0
            self.realised_negative[flux_label][:] = 0.0       
    
    def _check_valid_shortage(
        self, shortage: NDArray[np.float_], demand_negative: NDArray[np.float_]
    ) -> ValueError | None:
        if np.any(np.logical_and(self.demand > 0.0, shortage > 0.0)):
            raise ValueError("Invalid realised values: found shortage for positive demand")
        if np.any(shortage > np.absolute(demand_negative)):
            raise ValueError("Invalid realised values: found shortage larger than negative demand contributions")
        
    def _zeros_array(self) -> NDArray[np.float_]:
        return np.zeros(shape=self.shape, dtype=np.float_)
    
    def _init_arrays(self) -> None:
        self.demands = {}
        self.demands_negative = {}
        self.realised_negative = {}
        for flux_label in self.flux_labels:
            self.demands[flux_label] = self._zeros_array()
            self.demands_negative[flux_label] = self._zeros_array()
            self.realised_negative[flux_label] = self._zeros_array()
              
    @property
    def demand_negative(self) -> NDArray[np.float_]:
        """
        compute negative demand as sum of demands arrays
        """
        sum_array = np.stack(list(self.demands_negative.values()))
        return sum_array.sum(axis=0)
        
    @property
    def demand(self) -> NDArray[np.float_]:
        """
        compute demand as sum of demands arrays
        """
        sum_array = np.stack(list(self.demands.values()))
        return sum_array.sum(axis=0)
        

class exchange_ribasim_1d(exchange_balance):
    ribasim_infiltration: NDArray[Any]
    ribasim_drainage: NDArray[Any]

    def __init__(self, ribasim: RibasimApi) -> None:
        self.riba = ribasim
        self.ribasim_drainage = self.riba.get_value_ptr("drainage")
        self.ribasim_infiltration = self.riba.get_value_ptr("infiltration")
        self.ribasim_level = self.riba.get_value_ptr("level")
        exchange_balance.__init__(self, np.size(self.ribasim_drainage))
        self.demand["msw_ponding2riba_flux"] = np.zeros(
            shape=self.shape, dtype=np.float_
        )
        self.realised["msw_ponding2riba_flux"] = np.zeros(
            shape=self.shape, dtype=np.float_
        )

    def to_ribasim(self) -> None:
        if self.ribasim_drainage is not None:
            self.ribasim_drainage[:] = np.where(
                self.demand["sum"][:] > 0, self.demand["sum"][:], 0.0
            )
        if self.ribasim_infiltration is not None:
            self.ribasim_infiltration[:] = np.where(
                self.demand["sum"][:] < 0, self.demand["sum"][:], 0.0
            )

    def sum_demands(self) -> None:
        self.sum_keys = [
            "msw_ponding2riba_flux",
            "msw_sprinkling2riba_flux",
        ]
        super().sum_demands()
