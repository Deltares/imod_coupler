from typing import Any
from collections import ChainMap
import numpy as np
from numpy.typing import NDArray
from imod_coupler.kernelwrappers.mf6_wrapper import Mf6Drainage, Mf6River, Mf6Wrapper
from imod_coupler.drivers.ribametamod.ribametamod import days_to_seconds
from imod_coupler.drivers.ribametamod.mapping import SetMapping


class ExchangeBalance:
    demands: dict[str, NDArray[np.float_]]
    demands_negative: dict[str, NDArray[np.float_]]
    realised_negative: dict[str, NDArray[np.float_]]
    shape: int
    sum_keys: list[str]

    def __init__(self, shape: int, labels: list[str]) -> None:
        self.shape = shape
        self.flux_labels = labels
        self._init_arrays()

    def compute_realised(
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
        
        
class CoupledExchangeBalance(ExchangeBalance):
    demands: dict[str, NDArray[np.float_]]
    demands_negative: dict[str, NDArray[np.float_]]
    realised_negative: dict[str, NDArray[np.float_]]
    shape: int
    sum_keys: list[str]

    def __init__(self, shape: int, labels: list[str], 
                 mf6_river_packages: ChainMap[str, Mf6River],
                 mf6_drainage_packages: ChainMap[str, Mf6Drainage],
                 mapping: SetMapping,
                 ribasim_infiltration,
                 ribasim_drainage) -> None:
        self.mf6_river_packages = mf6_river_packages
        self.mf6_drainage_packages = mf6_drainage_packages
        self.mapping = mapping
        self.ribasim_infiltration = ribasim_infiltration
        self.ribasim_drainage = ribasim_drainage
        super.__init__(shape, labels)
        
    def reset(self) -> None:
        self.ribasim_infiltration[:] = 0.0
        self.ribasim_drainage[:] = 0.0
        ExchangeBalance.reset()
        
    def add_flux_estimate_mod(self, delt: float, mf6_head: NDArray[np.float_]) -> NDArray[np.float64]:
        # Compute MODFLOW 6 river and drain flux extimates
        for key, river in self.mf6_river_packages.items():
            river_flux = river.get_flux_estimate(mf6_head)
            river_flux_negative = np.where(river_flux < 0, river_flux, 0)
            self.demands[key] = self.mapping.mod2rib[key].dot(river_flux) / days_to_seconds(
                delt
            )
            self.demands_negative[key] = self.mapping.mod2rib[key].dot(river_flux_negative) / days_to_seconds(
                delt
            )
        for key, drainage in self.mf6_drainage_packages.items():
            drain_flux = drainage.get_flux_estimate(mf6_head)
            self.demands[key] = self.mapping.mod2rib[key].dot(drain_flux) / days_to_seconds(
                delt
            )
            
    def add_ponding_msw(self, delt:float, allocated_volume: NDArray) -> None:
        if self.mapping.msw2rib is not None:
            # flux from metaswap ponding to Ribasim
            if "sw_ponding" in self.mapping.msw2rib:
                allocated_flux_sec = (
                    allocated_volume
                    / days_to_seconds(delt)
                )
                self.demands["ponding_msw"] += self.mapping.msw2rib["sw_ponding"].dot(
                    allocated_flux_sec
                )[:]

    def to_ribasim(self) -> None:
        demand = self.demand
        self.ribasim_infiltration += np.where(demand > 0, demand, 0)
        self.ribasim_drainage += np.where(demand < 0, -demand, 0)
        
    def to_modflow(self, realised: NDArray) -> None:
        ExchangeBalance.compute_realised(realised)
        for flux_label in self.flux_labels:
            realised_fraction = np.where(np.nonzero(self.demands_negative[flux_label]), self.realised_negative[flux_label] / self.demands_negative[flux_label], 1.0)
            # correction only applies to Modflow cells which negatively contribute to the Ribasim volumes
            # in which case the Modflow demand was POSITIVE, otherwise the correction is 0
            qmf_corr = -(
                np.maximum(self.demands[flux_label], 0.0)
                * (1 - self.mapping.mod2rib[flux_label].transpose().dot(realised_fraction))
            )
        
     
