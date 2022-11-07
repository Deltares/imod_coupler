""" MetaMod: the coupling between MetaSWAP and MODFLOW 6

description:

"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import numpy as np
from loguru import logger
from numpy.typing import NDArray
from scipy.sparse import csr_matrix, dia_matrix
from xmipy import XmiWrapper

from imod_coupler.config import BaseConfig
from imod_coupler.drivers.dfm_metamod.config import Coupling, DfmMetaModConfig
from imod_coupler.drivers.dfm_metamod.dfm_wrapper import DfmWrapper
from imod_coupler.drivers.dfm_metamod.mf6_wrapper import MF6_Wrapper
from imod_coupler.drivers.driver import Driver
from imod_coupler.utils import Operator, create_mapping


class DfmMetaMod(Driver):
    """The driver coupling DFLOW-FM, MetaSWAP and MODFLOW 6"""

    name: str = "dfm_metamod"  # name of the driver
    base_config: BaseConfig  # the parsed information from the configuration file
    dfm_metamod_config: DfmMetaModConfig  # the parsed information from the configuration file specific to MetaMod
    coupling: Coupling  # the coupling information

    timing: bool  # true, when timing is enabled
    mf6: XmiWrapper  # the MODFLOW 6 XMI kernel
    msw: XmiWrapper  # the MetaSWAP XMI kernel
    dfm: DfmWrapper  # the dflow-fm BMI kernel

    max_iter: NDArray[Any]  # max. nr outer iterations in MODFLOW kernel
    delt: float  # time step from MODFLOW 6 (leading)

    mf6_head: NDArray[Any]  # the hydraulic head array in the groundwater model
    mf6_river_stage: NDArray[Any]  # the river stage array in the groundwater model

    dflowfm_1d_stage: NDArray[
        Any
    ]  # the river stage in the 1d rivers array in the surface water model

    number_dflowsteps_per_modflowstep = 10

    def __init__(
        self, base_config: BaseConfig, config_dir: Path, driver_dict: Dict[str, Any]
    ):
        """Constructs the `DfmMetaMod` object"""
        self.base_config = base_config
        self.dfm_metamod_config = DfmMetaModConfig(config_dir, **driver_dict)
        self.coupling = self.dfm_metamod_config.coupling[
            0
        ]  # Adapt as soon as we have multimodel support

    def initialize(self) -> None:
        self.mf6 = MF6_Wrapper(
            lib_path=self.dfm_metamod_config.kernels.modflow6.dll,
            lib_dependency=self.dfm_metamod_config.kernels.modflow6.dll_dep_dir,
            working_directory=Path(
                self.dfm_metamod_config.kernels.modflow6.work_dir.absolute()
            ),
            timing=self.base_config.timing,
        )
        self.msw = XmiWrapper(
            lib_path=self.dfm_metamod_config.kernels.metaswap.dll,
            lib_dependency=self.dfm_metamod_config.kernels.metaswap.dll_dep_dir,
            working_directory=Path(
                self.dfm_metamod_config.kernels.metaswap.work_dir.absolute()
            ),
            timing=self.base_config.timing,
        )

        # ================
        # modifying the path here should not be necessary
        os.environ["PATH"] = (
            os.path.dirname(self.dfm_metamod_config.kernels.dflowfm.dll)
            + os.pathsep
            + os.environ["PATH"]
        )
        # ================
        mdu_name = self.coupling.dict()["dfm_model"]
        dflowfm_input = self.dfm_metamod_config.kernels.dflowfm.work_dir.joinpath(
            mdu_name
        )
        self.dfm = DfmWrapper(engine="dflowfm", configfile=dflowfm_input)

        # Print output to stdout
        self.mf6.set_int("ISTDOUTTOFILE", 0)
        self.mf6.initialize()
        self.msw.initialize()
        self.dfm.initialize()

        self.log_version()
        self.couple()

    def log_version(self) -> None:
        logger.info(f"MODFLOW version: {self.mf6.get_version()}")
        logger.info(f"MetaSWAP version: {self.msw.get_version()}")
        logger.info(f"Dflow FM version: version fetching not implemented in BMI")

    def couple(self) -> None:
        """Couple Modflow and Metaswap"""
        # get some 'pointers' to MF6 and MSW internal data
        mf6_head_tag = self.mf6.get_var_address("X", self.coupling.mf6_model)
        self.mf6_head = self.mf6.get_value_ptr(mf6_head_tag)

    def update(self) -> None:

        # we cannot set the timestep (yet) in Modflow
        # -> set to the (dummy) value 0.0 for now
        self.mf6.prepare_time_step(0.0)
        self.delt = self.mf6.get_time_step()

        self.exchange_H_1D_t()
        self.exchange_V_1D()

        subtimestep_endtime = self.get_current_time()
        for _ in range(0, self.number_dflowsteps_per_modflowstep):
            subtimestep_endtime += self.delt / self.number_dflowsteps_per_modflowstep
            while self.dfm.get_current_time() < subtimestep_endtime:
                self.dfm.update()
        self.exchange_V_dash_1D()

        self.mf6.do_time_step()

        self.mf6.finalize_time_step()

    def finalize(self) -> None:
        self.mf6.finalize()
        self.msw.finalize()
        self.dfm.finalize()

    def get_current_time(self) -> float:
        return self.mf6.get_current_time()

    def get_end_time(self) -> float:
        return self.mf6.get_end_time()

    def exchange_H_1D_t(self) -> None:
        """
        From DFM to MF6.
        Waterlevels in the 1D-rivers at the beginning of the mf6-timestep. (T=t)
        Should be set as the MF6 river stages.
        MF6 unit: meters above MF6's reference plane
        DFM unit: ?
        """
        water_levels = self.dfm.get_waterlevels_1d()
        self.mf6.set_river_stages(
            self.coupling.mf6_model,
            self.coupling.mf6_river_pkg,
            water_levels,
        )

    def exchange_V_1D(self) -> None:
        """
        From MF6 to DFM.
        requested infiltration/drainage in the coming MF6 timestep for the 1D-rivers,
        estimated based on the MF6 groundwater levels and DFM water levels at T =t
        (so at the beginning of the timestep)
        MF6 unit: ?
        DFM unit: ?
        """
        pass

    def exchange_V_dash_1D(self) -> None:
        """
        From DFM to MF6
        the drainage/inflitration flux to the 1d rivers as realised by DFM is passed to modflow
        as a correction
        """
        pass

    def report_timing_totals(self) -> None:
        total_mf6 = self.mf6.report_timing_totals()
        total_msw = self.msw.report_timing_totals()
        total = total_mf6 + total_msw
        logger.info(f"Total elapsed time in numerical kernels: {total:0.4f} seconds")
