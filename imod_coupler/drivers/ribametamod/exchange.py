from typing import Any

import numpy as np
from numpy.typing import NDArray

from imod_coupler.kernelwrappers.mf6_wrapper import Mf6Wrapper
from imod_coupler.kernelwrappers.ribasim_wrapper import RibasimWrapper
from imod_coupler.utils import MemoryExchange


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

    def compute_realised(
        self, realised_volume: NDArray[np.float64], compute_volumes: bool = False
    ) -> None:
        """
        This function computes the realised (negative) volumes
        """
        shortage = self.demand - realised_volume
        demand_negative = self.demand_negative
        self._check_valid_shortage(
            shortage
        )  # use a numpy isclose to set the max non-zero value
        # deal with zero division
        self.realised_fraction[:] = np.where(
            demand_negative < 0.0, 1.0 - (shortage / demand_negative), 1.0
        )[:]
        if compute_volumes:
            for volume_label in self.volume_labels:
                self.realised_negative[volume_label] = (
                    self.demands_negative[volume_label] * self.realised_fraction
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
        self.realised_fraction = self._zeros_array()

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
    couplings: dict[str, MemoryExchange]

    def __init__(
        self,
        shape: int,
        labels: list[str],
        ribasim_kernel: RibasimWrapper,
        mf6_kernel: Mf6Wrapper,
        mf6_active_packages: list[str],
        mf6_passive_packages: list[str],
        mf6_api_packages: list[str],
    ) -> None:
        super().__init__(shape, labels)
        self.ribasim = ribasim_kernel
        self.mf6 = mf6_kernel
        self.mf6_active_packages = mf6_active_packages
        self.mf6_api_packages = mf6_api_packages
        self.mf6_passive_packages = mf6_passive_packages
        self.exchanged_ponding_per_dtsw = np.zeros_like(self.demand)
        self.coupled_basins = np.full_like(self.demand, True)

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
        for api_key, riv_key in zip(self.mf6_api_packages, self.mf6_active_packages):
            self.mf6.packages[api_key].hcof[:] = 0.0
            self.mf6.packages[api_key].nodelist[:] = self.mf6.packages[
                riv_key
            ].nodelist[:]
            self.mf6.packages[api_key].nbound[:] = self.mf6.packages[riv_key].nbound[:]

    def reset(self) -> None:
        self.ribasim.drainage_infiltration[:] = 0.0
        super().reset()
        self.update_api_packages()
        # reset cummulative array for subtimestepping
        self.exchanged_ponding_per_dtsw[:] = 0.0

    def add_flux_estimate_mod(
        self, mf6_head: NDArray[np.float64], delt_gw: float
    ) -> None:
        # Compute MODFLOW 6 river and drain flux extimates
        for package_name in self.mf6_active_packages:
            self.mf6.packages[package_name].set_flux_estimate(mf6_head)
            # Flux estimation is always in m3/d; exchange as volume per delt_gw
            self.couplings[package_name].exchange(delt=(1 / delt_gw))
            # only negative contributions
            self.couplings[package_name + "_negative"].exchange(delt=(1 / delt_gw))
            # Swap sign since a negative RIV flux means a positive contribution to Ribasim
            self.demands_mf6[package_name] = -self.mf6.packages[package_name].q_estimate
        for package_name in self.mf6_passive_packages:
            self.mf6.packages[package_name].set_flux_estimate(mf6_head)
            # Flux estimation is always in m3/d; exchange as volume per delt_gw
            self.couplings[package_name].exchange(delt=(1 / delt_gw))

    def add_ponding_volume_msw(self) -> None:
        # sw_ponding volumes are accumulated over the delt_gw timestep,
        # resulting in a total volume per delt_gw
        if "sw_ponding" in self.couplings.keys():
            self.couplings["sw_ponding"].add()

    def flux_to_ribasim(self, delt_gw: float, delt_sw: float) -> None:
        demand_per_subtimestep = self.get_demand_flux_sec(delt_gw, delt_sw)
        # exchange to Ribasim; negative demand in exchange class means infiltration from Ribasim
        self.ribasim.drainage_infiltration[:] = demand_per_subtimestep[:]
        self.ribasim.exchange_infiltration_drainage(self.coupled_basins)

    def flux_to_modflow(
        self, realised_volume: NDArray[np.float64], delt_gw: float
    ) -> None:
        if not self.mf6_active_packages:
            return  # no active coupling
        super().compute_realised(realised_volume)
        for api_key in self.mf6_api_packages:
            # correction only applies to MF6 cells which negatively contribute to the Ribasim volumes
            # correction as extraction from MF6 model.
            # demands in exchange class are volumes per delt_gw, RHS needs a flux in m3/day
            self.couplings[api_key].exchange()

    def get_demand_flux_sec(self, delt_gw: float, delt_sw: float) -> Any:
        # returns the MODFLOW6 demands and MetaSWAP demands as a flux in m3/s
        mf6_labels = list(self.demands.keys())
        msw_demand_flux = 0.0
        if "sw_ponding" in mf6_labels:
            mf6_labels.remove("sw_ponding")
            msw_demand_flux = (
                self.demands["sw_ponding"] - self.exchanged_ponding_per_dtsw
            ) / delt_sw
            # update the ponding demand volume exchanged to Ribasim.
            self.exchanged_ponding_per_dtsw[:] = self.demands["sw_ponding"][:]
        demands = {key: self.demands[key] for key in mf6_labels}
        mf6_demand_flux = np.stack(list(demands.values())).sum(axis=0) / delt_gw
        return (mf6_demand_flux + msw_demand_flux) / day_to_seconds

    def log(self, itime: float) -> None:
        # flux estimations
        for key in self.mf6_active_packages + self.mf6_passive_packages:
            self.couplings[key].log(itime)
        # runoff
        if "sw_ponding" in self.demands.keys():
            self.couplings["sw_ponding"].log(itime)
        for key in self.mf6_api_packages:
            self.couplings[key].log(itime)


day_to_seconds = 86400
