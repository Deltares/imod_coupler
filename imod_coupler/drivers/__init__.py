from typing import List, Type

from imod_coupler.drivers.dfm_metamod.dfm_metamod_driver import DfmMetaModDriver
from imod_coupler.drivers.driver import Driver
from imod_coupler.drivers.metamod.metamod import MetaMod

Drivers: List[Type[Driver]] = [MetaMod, DfmMetaModDriver]
