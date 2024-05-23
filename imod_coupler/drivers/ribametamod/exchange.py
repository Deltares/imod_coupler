from collections import ChainMap
from typing import Any

import numpy as np
from numpy.typing import NDArray

from imod_coupler.drivers.ribametamod.mapping import SetMapping
from imod_coupler.kernelwrappers.mf6_wrapper import (
    Mf6Api,
    Mf6Drainage,
    Mf6River,
)
from imod_coupler.logging.exchange_collector import ExchangeCollector


class ExchangeBalance:
    demands: dict[str, NDArray[np.float64]]
    demands_negative: dict[str, NDArray[np.float64]]
    demands_mf6: dict[str, NDArray[np.float64]]
    realised_negative: dict[str, NDArray[np.float64]]
    shape: int
    sum_keys: list[str]

    def __init__(self, shape: int, labels: list[str]) -> None:
        self.shape = shape
        self.flux_labels = labels
        self._init_arrays()

    def compute_realised(self, realised: NDArray[np.float64]) -> None:
        """
        This function computes the realised (negative) volumes
        """
        shortage = np.absolute(self.demand - realised)
        demand_negative = self.demand_negative
        self._check_valid_shortage(shortage, demand_negative)
        # deal with zero division
        realised_fraction = np.where(
            demand_negative < 0.0, 1.0 - (-shortage / demand_negative), 1.0
        )
        for flux_label in self.flux_labels:
            self.realised_negative[flux_label] = (
                self.demands_negative[flux_label] * realised_fraction
            )

    def reset(self) -> None:
        """
        function sets all arrays to zero
        """
        for flux_label in self.flux_labels:
            self.demands[flux_label][:] = 0.0
            self.demands_negative[flux_label][:] = 0.0
            self.realised_negative[flux_label][:] = 0.0

    def _check_valid_shortage(
        self, shortage: NDArray[np.float64], demand_negative: NDArray[np.float64]
    ) -> None:
        if np.any(np.logical_and(self.demand > 0.0, shortage > 0.0)):
            raise ValueError(
                "Invalid realised values: found shortage for positive demand"
            )
        if np.any(shortage > np.absolute(demand_negative)):
            raise ValueError(
                "Invalid realised values: found shortage larger than negative demand contributions"
            )

    def _zeros_array(self) -> NDArray[np.float64]:
        return np.zeros(shape=self.shape, dtype=np.float64)

    def _init_arrays(self) -> None:
        self.demands = {}
        self.demands_mf6 = {}
        self.demands_negative = {}
        self.realised_negative = {}
        for flux_label in self.flux_labels:
            self.demands[flux_label] = self._zeros_array()
            self.demands_negative[flux_label] = self._zeros_array()
            self.realised_negative[flux_label] = self._zeros_array()

    @property
    def demand_negative(self) -> Any:
        """
        compute negative demand as sum of demands arrays
        """
        sum_array = np.stack(list(self.demands_negative.values()))
        return sum_array.sum(axis=0)

    @property
    def demand(self) -> Any:
        """
        compute demand as sum of demands arrays
        """
        sum_array = np.stack(list(self.demands.values()))
        return sum_array.sum(axis=0)


class CoupledExchangeBalance(ExchangeBalance):
    demands: dict[str, NDArray[np.float64]]
    demands_mf6: dict[str, NDArray[np.float64]]
    demands_negative: dict[str, NDArray[np.float64]]
    realised_negative: dict[str, NDArray[np.float64]]
    shape: int
    sum_keys: list[str]
    exchange_logger: ExchangeCollector

    def __init__(
        self,
        shape: int,
        labels: list[str],
        mf6_river_packages: ChainMap[str, Mf6River],
        mf6_drainage_packages: ChainMap[str, Mf6Drainage],
        mf6_active_river_api_packages: dict[str, Mf6Api],
        mapping: SetMapping,
        ribasim_infiltration: NDArray[Any],
        ribasim_drainage: NDArray[Any],
        exchange_logger: ExchangeCollector,
    ) -> None:
        super().__init__(shape, labels)
        self.mf6_river_packages = mf6_river_packages
        self.mf6_active_river_api_packages = mf6_active_river_api_packages
        self.mf6_drainage_packages = mf6_drainage_packages
        self.mapping = mapping
        self.ribasim_infiltration = ribasim_infiltration
        self.ribasim_drainage = ribasim_drainage
        self.exchange_logger = exchange_logger

    def update_api_packages(self) -> None:
        """
        Updates the api packages by:

        1- Setting package hcof to zeros
        2- Setting the values in the nodelist to the values of the corresponding riv-package
        3- Setting the nbound value to the one of the riv-package. In other boundary packages
        this is done automatically by reading in period data

        The update of the nbound and nodelist should be done after every timestep where new input is
        read in the riv package.

        """
        for key in self.mf6_active_river_api_packages.keys():
            self.mf6_active_river_api_packages[key].hcof[:] = 0.0
            self.mf6_active_river_api_packages[key].nodelist[:] = (
                self.mf6_river_packages[key].nodelist[:]
            )
            self.mf6_active_river_api_packages[key].nbound[:] = self.mf6_river_packages[
                key
            ].nbound[:]

    def reset(self) -> None:
        self.ribasim_infiltration[:] = 0.0
        self.ribasim_drainage[:] = 0.0
        super().reset()
        self.update_api_packages()

    def add_flux_estimate_mod(self, delt: float, mf6_head: NDArray[np.float64]) -> None:
        # Compute MODFLOW 6 river and drain flux extimates
        for key, river in self.mf6_river_packages.items():
            # Swap sign since a negative RIV flux means a positive contribution to Ribasim
            river_flux = -river.get_flux_estimate(mf6_head)
            river_flux_negative = np.where(river_flux < 0, river_flux, 0)
            self.demands_mf6[key] = river_flux[:] / days_to_seconds(delt)
            self.demands[key] = self.mapping.map_mod2rib[key].dot(self.demands_mf6[key])
            self.demands_negative[key] = self.mapping.map_mod2rib[key].dot(
                river_flux_negative
            ) / days_to_seconds(delt)
        for key, drainage in self.mf6_drainage_packages.items():
            # Swap sign since a negative RIV flux means a positive contribution to Ribasim
            drain_flux = -drainage.get_flux_estimate(mf6_head)
            self.demands[key] = self.mapping.map_mod2rib[key].dot(
                drain_flux
            ) / days_to_seconds(delt)

    def log_demands(self, current_time: float) -> None:
        for key, array in self.demands.items():
            self.exchange_logger.log_exchange(
                ("exchange_demand_" + key), self.demands[key], current_time
            )

    def add_ponding_msw(
        self, delt: float, allocated_volume: NDArray[np.float64]
    ) -> None:
        if self.mapping.msw2rib is not None:
            # flux from metaswap ponding to Ribasim
            if "sw_ponding" in self.mapping.msw2rib:
                allocated_flux_sec = allocated_volume / days_to_seconds(delt)
                self.demands["sw_ponding"] += self.mapping.msw2rib["sw_ponding"].dot(
                    allocated_flux_sec
                )[:]

    def to_ribasim(self) -> None:
        demand = self.demand
        # negative demand in exchange class means infiltration from Ribasim
        coupled_index = self.mapping.coupled_mod2rib
        self.ribasim_infiltration[coupled_index] = np.where(demand < 0, -demand, 0)[
            coupled_index
        ]
        self.ribasim_drainage[coupled_index] = np.where(demand > 0, demand, 0)[
            coupled_index
        ]

    def to_modflow(self, realised: NDArray[np.float64]) -> None:
        super().compute_realised(realised)
        for key in self.mf6_active_river_api_packages.keys():
            realised_fraction = np.where(
                np.isclose(self.demands_negative[key], 0.0),
                1.0,
                self.realised_negative[key] / self.demands_negative[key],
            )
            # correction only applies to Modflow cells which negatively contribute to the Ribasim volumes
            # in which case the Modflow demand was POSITIVE, otherwise the correction is 0
            self.mf6_active_river_api_packages[key].rhs[:] = -(
                np.maximum(self.demands_mf6[key], 0.0)
                * (1 - self.mapping.map_rib2mod_flux[key].dot(realised_fraction))
            )


def days_to_seconds(day: float) -> float:
    return day * 86400
