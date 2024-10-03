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
        self.volume_labels = labels
        self._init_arrays()

    def compute_realised(self, realised_volume: NDArray[np.float64]) -> None:
        """
        This function computes the realised (negative) volumes
        """
        shortage = self.demand - realised_volume
        demand_negative = self.demand_negative
        self._check_valid_shortage(
            shortage
        )  # use a numpy isclose to set the max non-zero value
        # deal with zero division
        realised_fraction = np.where(
            demand_negative < 0.0, 1.0 - (shortage / demand_negative), 1.0
        )
        for volume_label in self.volume_labels:
            self.realised_negative[volume_label] = (
                self.demands_negative[volume_label] * realised_fraction
            )

    def reset(self) -> None:
        """
        function sets all arrays to zero
        """
        for volume_label in self.volume_labels:
            self.demands[volume_label][:] = 0.0
            self.demands_negative[volume_label][:] = 0.0
            self.realised_negative[volume_label][:] = 0.0

    def _check_valid_shortage(self, shortage: NDArray[np.float64]) -> None:
        eps: float = 1.0e-04
        if np.any(np.logical_and(self.demand > 0.0, np.absolute(shortage) > eps)):
            raise ValueError(
                "Invalid realised volumes: found shortage for positive demand"
            )
        if np.any(shortage < self.demand_negative - eps):
            raise ValueError(
                "Invalid realised volumes: found shortage larger than negative demand contributions"
            )

    def _zeros_array(self) -> NDArray[np.float64]:
        return np.zeros(shape=self.shape, dtype=np.float64)

    def _init_arrays(self) -> None:
        self.demands = {}
        self.demands_mf6 = {}
        self.demands_negative = {}
        self.realised_negative = {}
        for volume_label in self.volume_labels:
            self.demands[volume_label] = self._zeros_array()
            self.demands_negative[volume_label] = self._zeros_array()
            self.realised_negative[volume_label] = self._zeros_array()

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
        self.exchanged_ponding_per_dtsw = np.zeros_like(self.demand)

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
        # reset cummulative array for subtimestepping
        self.exchanged_ponding_per_dtsw[:] = 0.0

    def add_flux_estimate_mod(
        self, mf6_head: NDArray[np.float64], delt_gw: float
    ) -> None:
        # Compute MODFLOW 6 river and drain flux extimates
        for key, river in self.mf6_river_packages.items():
            # Swap sign since a negative RIV flux means a positive contribution to Ribasim
            # Flux estimation is always in m3/d; add to demands as volume per delt_gw
            river_flux = -river.get_flux_estimate(mf6_head) * delt_gw
            river_flux_negative = np.where(river_flux < 0, river_flux, 0)
            self.demands_mf6[key] = river_flux[:]
            self.demands[key] = self.mapping.map_mod2rib[key].dot(self.demands_mf6[key])
            self.demands_negative[key] = self.mapping.map_mod2rib[key].dot(
                river_flux_negative
            )
        for key, drainage in self.mf6_drainage_packages.items():
            # Swap sign since a negative RIV flux means a positive contribution to Ribasim
            drain_flux = -drainage.get_flux_estimate(mf6_head) * delt_gw
            self.demands[key] = self.mapping.map_mod2rib[key].dot(drain_flux)

    def add_ponding_volume_msw(self, allocated_volume: NDArray[np.float64]) -> None:
        if self.mapping.msw2rib is not None:
            # sw_ponding volumes are accumulated over the delt_gw timestep,
            # resulting in a total volume per delt_gw
            if "sw_ponding" in self.mapping.msw2rib:
                self.demands["sw_ponding"] += self.mapping.msw2rib["sw_ponding"].dot(
                    allocated_volume
                )[:]

    def flux_to_ribasim(self, delt_gw: float, delt_sw: float) -> None:
        demand_per_subtimestep = self.get_demand_flux_sec(delt_gw, delt_sw)

        # exchange to Ribasim; negative demand in exchange class means infiltration from Ribasim
        self.ribasim_infiltration[self.mapping.coupled_index] = np.where(
            demand_per_subtimestep < 0, -demand_per_subtimestep, 0
        )[self.mapping.coupled_index]
        self.ribasim_drainage[self.mapping.coupled_index] = np.where(
            demand_per_subtimestep > 0, demand_per_subtimestep, 0
        )[self.mapping.coupled_index]

    def flux_to_modflow(
        self, realised_volume: NDArray[np.float64], delt_gw: float
    ) -> None:
        if not self.mf6_river_packages:
            return  # no active coupling
        super().compute_realised(realised_volume)
        for key in self.mf6_active_river_api_packages.keys():
            realised_fraction = np.where(
                np.isclose(self.demands_negative[key], 0.0),
                1.0,
                self.realised_negative[key] / self.demands_negative[key],
            )
            # correction only applies to MF6 cells which negatively contribute to the Ribasim volumes
            # correction as extraction from MF6 model.
            # demands in exchange class are volumes per delt_gw, RHS needs a flux in m3/day
            self.mf6_active_river_api_packages[key].rhs[:] = -(
                np.minimum(self.demands_mf6[key] / delt_gw, 0.0)
            ) * (1 - self.mapping.map_rib2mod_flux[key].dot(realised_fraction))

    def get_demand_flux_sec(self, delt_gw: float, delt_sw: float) -> Any:
        # returns the MODFLOW6 demands and MetaSWAP demands as a flux in m3/s
        mf6_labels = list(self.demands.keys())
        mf6_labels.remove("sw_ponding")
        demands = {key: self.demands[key] for key in mf6_labels}
        mf6_demand_flux = np.stack(list(demands.values())).sum(axis=0) / delt_gw
        msw_demand_flux = (
            self.demands["sw_ponding"] - self.exchanged_ponding_per_dtsw
        ) / delt_sw

        # update the ponding demand volume exchanged to Ribasim.
        self.exchanged_ponding_per_dtsw[:] = self.demands["sw_ponding"][:]

        return (mf6_demand_flux + msw_demand_flux) / day_to_seconds

    def log_demands(self, current_time: float) -> None:
        for key, array in self.demands.items():
            if "sw_ponding" not in key:
                self.exchange_logger.log_exchange(
                    ("exchange_demand_" + key), array, current_time
                )
        for key in self.mf6_active_river_api_packages.keys():
            if "sw_ponding" not in key:
                self.mf6_active_river_api_packages[key].rhs[:]
                self.exchange_logger.log_exchange(
                    ("exchange_correction_" + key), array, current_time
                )
        self.exchange_logger.log_exchange(
            ("exchange_demand_sw_ponding"),
            self.demands["sw_ponding"],
            current_time,
        )


day_to_seconds = 86400
