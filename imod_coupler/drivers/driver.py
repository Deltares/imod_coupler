from __future__ import annotations

import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
import __main__

from loguru import logger
from imod_coupler.config import BaseConfig
from imod_coupler.drivers.metamod.metamod import MetaMod
from imod_coupler.drivers.ribametamod.ribametamod import RibaMetaMod
from imod_coupler.drivers.ribamod.ribamod import RibaMod

def resolve_path(libname: str) -> str:
    match sys.platform.lower():
        case "win32":
            env_var = "PATH"
        case "linux" | "linux2" | "darwin":
            env_var = "LD_LIBRARY_PATH"
        case _:
            return libname

    if os.path.isfile(libname):
        return libname
    if env_var in os.environ:
        pathdef: str = os.environ[env_var]
        for dir in pathdef.split(os.pathsep):
            full_path = Path(dir) / libname
            if full_path.is_file():
                return str(full_path)
    return libname  # if resolution failed, give it back to the call site


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

    # resolve library locations using which
    for kernel in config_dict["driver"]["kernels"].values():
        if "dll" in kernel:
            kernel["dll"] = resolve_path(kernel["dll"])

    # construct a driver instance for the driver type specified in the config
    obj={s.lower():s for s in dir(__main__)}
    drv=base_config.driver_type.lower()
    if drv in obj:
        return getattr(__main__,obj[drv])(
            base_config=base_config,
            driver_config=config_dict,
            config_dir=config_dir,
        )
    else:
        raise ValueError(f"Driver type {base_config.driver_type} is not supported.")
