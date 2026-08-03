from __future__ import annotations

import copy
import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from loguru import logger
from mpi4py import MPI

from imod_coupler.config import BaseConfig


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


def init_hpc(
    config_dict_used: dict[str, Any], config_dir: Path, base_config: BaseConfig
) -> dict[str, Any]:

    bool_parallel = False
    if len(base_config.hpc) > 0:
        mpi_comm = MPI.COMM_WORLD
        mpi_size = mpi_comm.Get_size()
        mpi_rank = mpi_comm.Get_rank()
        if mpi_size > 1:
            bool_parallel = True

    if bool_parallel:
        # Read the HPC file with MPI ranks defined for each MODFLOW 6 submodel.
        hpc_path = Path(config_dir / base_config.hpc)
        # read the HPC file
        if hpc_path.is_file():
            with open(hpc_path) as file:
                s = file.read()
            lst = list(map(str.strip, s.split("\n")))
            lst = [x for x in lst if (len(x) > 0 and x[0] != "#")]
            i0 = list(map(str.lower, lst)).index("begin partitions")
            i1 = list(map(str.lower, lst)).index("end partitions")
            lst = lst[i0 + 1 : i1]
            mf6_mpi_rank = {}
            for item in lst:
                mf6_mpi_rank[item.split()[0]] = int(item.split()[1])
        else:
            raise ValueError(f"Can't find {hpc_path}.")

        # Determine the MPI ranks for the MetaSWAP submodels.
        msw_mpi_rank: dict[str, int] = {}
        for coupling in config_dict_used["driver"]["coupling"]:
            mf6_model = coupling["mf6_model"]
            msw_model = coupling["msw_model"]
            msw_mpi_rank[msw_model] = mf6_mpi_rank[mf6_model]

        # Determine the new list of MetaSWAP submodels
        msw_model_list = []
        msw_models = []
        for msw_dict in config_dict_used["driver"]["kernels"]["metaswap"]:
            msw_model = msw_dict["msw_model"]
            if msw_mpi_rank[msw_model] == mpi_rank:
                msw_model_list.append(msw_dict)
                msw_model_list[-1]["mpi_rank"] = mpi_rank
                msw_models.append(msw_model)
        config_dict_used["driver"]["kernels"]["metaswap"] = msw_model_list

        coupling_list = []
        for coupling in config_dict_used["driver"]["coupling"]:
            # Fow now, only check for presence of MetaSWAP. FUTURE: include MODFLOW
            msw_model = coupling["msw_model"]
            if msw_model in msw_models:
                coupling_list.append(coupling)
        config_dict_used["driver"]["coupling"] = coupling_list

        return config_dict_used
    else:
        return config_dict_used


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
    from imod_coupler.drivers.ribametamod.config import RibaMetaModConfig
    from imod_coupler.drivers.ribametamod.ribametamod import RibaMetaMod
    from imod_coupler.drivers.ribamod.config import RibaModConfig
    from imod_coupler.drivers.ribamod.ribamod import RibaMod

    # resolve library locations using which
    for kernel in config_dict["driver"]["kernels"].values():
        if isinstance(kernel, list):
            for i in range(len(kernel)):
                if "dll" in kernel[i]:
                    kernel[i]["dll"] = resolve_path(kernel[i]["dll"])
        else:
            if "dll" in kernel:
                kernel["dll"] = resolve_path(kernel["dll"])

    if base_config.driver_type == "metamod":
        config_dict_used = copy.deepcopy(config_dict)

        # check for the coupling to be a list
        if not isinstance(config_dict["driver"]["coupling"], list):
            config_dict_used["driver"]["coupling"] = [config_dict["driver"]["coupling"]]

        # Filter for parallel computing
        config_dict_used = init_hpc(config_dict_used, config_dir, base_config)

        metamod_config = MetaModConfig(
            config_dir=config_dir, **config_dict_used["driver"]
        )
        if base_config.modflow_newton_formulation:
            raise NotImplementedError(
                "The MODFLOW Newton formulation is not yet implemented for MetaMod. "
                "Please set modflow_newton_formulation to false in the config file."
            )
        return MetaMod(base_config, metamod_config)
    elif base_config.driver_type == "ribamod":
        ribamod_config = RibaModConfig(config_dir=config_dir, **config_dict["driver"])
        return RibaMod(base_config, ribamod_config)
    elif base_config.driver_type == "ribametamod":
        config_dict_used = copy.deepcopy(config_dict)

        # check for the coupling to be a list
        if not isinstance(config_dict["driver"]["coupling"], list):
            config_dict_used["driver"]["coupling"] = [config_dict["driver"]["coupling"]]

        ribametamod_config = RibaMetaModConfig(
            config_dir=config_dir, **config_dict_used["driver"]
        )
        return RibaMetaMod(base_config, ribametamod_config)
    else:
        raise ValueError(f"Driver type {base_config.driver_type} is not supported.")
