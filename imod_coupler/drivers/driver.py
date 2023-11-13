from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from loguru import logger

from imod_coupler.config import BaseConfig


class Driver(ABC):
    """Driver base class

    Inherit from this class when creating a new driver
    """

    def execute(self) -> None:
        """Execute the driver"""

        # This will initialize and couple the kernels
        self.initialize()

        # Run the time loop
        while self.get_current_time() < self.get_end_time():
            self.update()

        logger.info("New simulation terminated normally")

        self.finalize()

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the coupled models"""
        ...

    @abstractmethod
    def update(self) -> None:
        """Perform a single time step"""
        ...

    @abstractmethod
    def finalize(self) -> None:
        """Cleanup the resources"""
        ...

    @abstractmethod
    def get_current_time(self) -> float:
        """Return current time"""
        ...

    @abstractmethod
    def get_end_time(self) -> float:
        """Return end time"""
        ...

    @abstractmethod
    def report_timing_totals(self) -> None:
        """Report total time spent on coupling"""
        ...


def get_driver(
    config_dict: dict[str, Any], config_dir: Path, base_config: BaseConfig
) -> Driver:
    from imod_coupler.drivers.metamod.config import MetaModConfig
    from imod_coupler.drivers.metamod.metamod import MetaMod
    from imod_coupler.drivers.ribamod.config import RibaModConfig
    from imod_coupler.drivers.ribamod.ribamod import RibaMod
    from imod_coupler.drivers.ribametamod.config import RibaMetaModConfig
    from imod_coupler.drivers.ribametamod.ribametamod import RibaMetaMod
    if base_config.driver_type == "metamod":
        metamod_config = MetaModConfig(config_dir=config_dir, **config_dict["driver"])
        return MetaMod(base_config, metamod_config)
    elif base_config.driver_type == "ribamod":
        ribamod_config = RibaModConfig(config_dir=config_dir, **config_dict["driver"])
        return RibaMod(base_config, ribamod_config)
    elif base_config.driver_type == "ribametamod":
        ribametamod_config = RibaMetaModConfig(config_dir=config_dir, **config_dict["driver"])
        return RibaMetaMod(base_config, ribametamod_config)
    else:
        raise ValueError(f"Driver type {base_config.driver_type} is not supported.")
