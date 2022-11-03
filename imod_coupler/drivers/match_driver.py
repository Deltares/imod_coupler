from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from imod_coupler.config import BaseConfig
from imod_coupler.drivers import Drivers
from imod_coupler.drivers.dfm_metamod.config import DfmMetaModConfig
from imod_coupler.drivers.driver import Driver
from imod_coupler.drivers.metamod.config import MetaModConfig
from imod_coupler.drivers.metamod.metamod import MetaMod


def match_driver(
    driver_type: str,
    config_dir: Path,
    base_config: BaseConfig,
    driver_dict: Dict[str, Any],
) -> Driver:
    """Returns the correct driver following the `driver_type` parameter

    Parameters
    ----------
    driver_type : str
        Determines which driver is returned
    config_dir : Path
        The directory where the config file resides
    base_config : BaseConfig
        The base config
    driver_dict : Dict[str, Any]
        The part of the configuration file concerning the driver

    Returns
    -------
    Driver
        The requested driver object

    Raises
    ------
    ValueError
        Raised if an invalid driver type is requested
    """

    for Driver in Drivers:
        if Driver.name == driver_type:
            return Driver(base_config, config_dir, driver_dict)

    raise ValueError(f"Driver type {base_config.driver_type} is not supported.")
