""" MetaMod: the coupling between MetaSWAP and MODFLOW 6

description:

"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

import numpy as np
import scipy.sparse as spr
from loguru import logger
from numpy.typing import NDArray
from scipy.sparse import csr_matrix, dia_matrix
from xmipy import XmiWrapper

from imod_coupler.config import BaseConfig
from imod_coupler.drivers.dfm_metamod.config import Coupling, DfmMetaModConfig
from imod_coupler.drivers.dfm_metamod.dfm_wrapper import DfmWrapper
from imod_coupler.drivers.dfm_metamod.mapping_functions import (
    calc_correction,
    get_dflow1d_lookup,
    get_svat_lookup,
    mapping_active_mf_dflow1d,
    mapping_mf_msw,
)
from imod_coupler.drivers.dfm_metamod.mf6_wrapper import Mf6Wrapper
from imod_coupler.drivers.dfm_metamod.msw_wrapper import MswWrapper
from imod_coupler.drivers.driver import Driver
from imod_coupler.utils import Operator, create_mapping


class DfmMetaMod(Driver):
    """The driver coupling DFLOW-FM, MetaSWAP and MODFLOW 6"""

    name: str = "dfm_metamod"  # name of the driver
    base_config: BaseConfig  # the parsed information from the configuration file
    dfm_metamod_config: DfmMetaModConfig  # the parsed information from the configuration file specific to MetaMod
    coupling: Coupling  # the coupling information

    timing: bool  # true, when timing is enabled
    mf6: Mf6Wrapper  # the MODFLOW 6 XMI kernel
    msw: MswWrapper  # the MetaSWAP XMI kernel
    dfm: DfmWrapper  # the dflow-fm BMI kernel

    max_iter: NDArray[np.int_]  # max. nr outer iterations in MODFLOW kernel
    delt: float  # time step from MODFLOW 6 (leading)
    msw_time: float  # MetaSWAP current time

    # dictionary used for converting x, y coordinates to node numbers for dflow-fm
    dflow1d_lookup: dict[tuple[float, float], int]

    # dictionary used for converting metaswap external svat id's to internal svat id's
    svat_lookup: dict[tuple[float, float], int]

    # sparse matrices used for  modflow-dflow exchanges
    map_active_mod_dflow1d: dict[str, csr_matrix]
    # masks used for  modflow-dflow exchanges
    mask_active_mod_dflow1d: dict[str, NDArray[np.int_]]

    # sparse matrices used for modflow-metaswap exchanges
    map_mf_msw: dict[str, csr_matrix]
    # masks used for modflow-metaswap exchanges
    mask_mf_msw: dict[str, NDArray[np.int_]]

    # tolerance for time-related comparisons
    time_eps = 1e-5

    def __init__(
        self, base_config: BaseConfig, config_dir: Path, driver_dict: Dict[str, Any]
    ):
        """Constructs the `DfmMetaMod` object"""
        self.base_config = base_config
        self.dfm_metamod_config = DfmMetaModConfig(config_dir, **driver_dict)
        self.coupling = self.dfm_metamod_config.coupling[
            0
        ]  # Adapt as soon as we have multimodel support

        self.dflow1d_lookup = get_dflow1d_lookup(self.coupling.dfm_1d_points_dat)
        (
            self.map_active_mod_dflow1d,
            self.mask_active_mod_dflow1d,
        ) = mapping_active_mf_dflow1d(
            self.coupling.mf6_river_to_dfm_1d_q_dmm,
            self.coupling.dfm_1d_waterlevel_to_mf6_river_stage_dmm,
            self.dflow1d_lookup,
        )
        
        self.svat_lookup = get_svat_lookup(self.msw.working_directory)
        self.mf6.
        
        self.map_mod_msw, self.mask_mod_msw = mapping_mf_msw(
            self.svat_lookup, self.array_dims, self.conversion_matrix
        )

    def initialize(self) -> None:

        self.mf6 = Mf6Wrapper(
            lib_path=self.dfm_metamod_config.kernels.modflow6.dll,
            lib_dependency=self.dfm_metamod_config.kernels.modflow6.dll_dep_dir,
            working_directory=self.dfm_metamod_config.kernels.modflow6.work_dir,
            timing=self.base_config.timing,
        )

        self.msw = MswWrapper(
            lib_path=self.dfm_metamod_config.kernels.metaswap.dll,
            lib_dependency=self.dfm_metamod_config.kernels.metaswap.dll_dep_dir,
            working_directory=self.dfm_metamod_config.kernels.metaswap.work_dir,
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

        # if self.coupling.enable_sprinkling:
        # in this case we have a sprinkling demand from MetaSWAP

    def update(self) -> None:

        # heads from modflow to MetaSWAP
        self.exchange_mod2msw()

        # we cannot set the timestep (yet) in Modflow
        # -> set to the (dummy) value 0.0 for now
        t_begin = self.get_current_time()
        self.mf6.prepare_time_step(0.0)

        self.delt = self.mf6.get_time_step()
        self.msw.prepare_time_step(self.delt)

        # stage from dflow 1d to modflow
        self.exchange_H_1D_t()
        # flux from modflow to dflow 1d
        self.exchange_V_1D()

        # get cum flux mf->fm pre-timestep and store locally
        self.store_1d_river_fluxes_to_dfm()

        # sub timestepping between metaswap and dflow
        subtimestep_endtime = t_begin
        for _ in range(self.number_dflowsteps_per_modflowstep):
            subtimestep_endtime += self.delt / self.number_dflowsteps_per_modflowstep

            while (
                self.dfm.get_current_time()
                < days_to_seconds(subtimestep_endtime) - self.time_eps
            ):
                self.dfm.update()
        self.exchange_V_dash_1D()

        # get cum flux new and calculate correction
        # apply correction to fm -> gives a modflow array

        # convergence loop modflow-metaswap
        self.mf6.prepare_solve(1)
        for kiter in range(1, self.max_iter + 1):
            has_converged = self.do_iter_mf_msw(1)
            if has_converged:
                logger.debug(f"MF6-MSW converged in {kiter} iterations")
                break
        self.mf6.finalize_solve(1)

        self.mf6.finalize_time_step()
        self.msw_time = self.mf6.get_current_time()
        self.msw.finalize_time_step()

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
        dfm_water_levels = self.dfm.get_waterlevels_1d()
        mf6_river_stage = self.mf6.get_river_stages(
            self.coupling.mf6_model, self.coupling.mf6_river_pkg
        )

        updated_river_stage = (
            self.mask_active_mod_dflow1d["dflow1d2mf-riv_stage"][:] * mf6_river_stage[:]
            + self.map_active_mod_dflow1d["dflow1d2mf-riv_stage"].dot(dfm_water_levels)[
                :
            ]
        )

        self.mf6.set_river_stages(
            self.coupling.mf6_model,
            self.coupling.mf6_river_pkg,
            updated_river_stage,
        )

    def exchange_V_1D(self) -> None:
        """
        From MF6 to DFM.
        requested infiltration/drainage in the coming MF6 timestep for the 1D-rivers,
        estimated based on the MF6 groundwater levels and DFM water levels at T =t
        (so at the beginning of the timestep)
        Also recomputes the weights that should be used for the correction flux.
        MF6 unit: ?
        DFM unit: ?
        """
        mf6_river_aquifer_flux = self.mf6.get_river_flux(
            self.coupling.mf6_model, self.coupling.mf6_river_pkg
        )
        dflow1d_flux_receive = self.dfm.get_1d_river_fluxes()
        if dflow1d_flux_receive is None:
            raise ValueError("dflow 1d river flux not found")
        dflow1d_flux_receive = (
            self.mask_active_mod_dflow1d["mf-riv2dflow1d_flux"][:]
            * dflow1d_flux_receive[:]
            + self.map_active_mod_dflow1d["mf-riv2dflow1d_flux"].dot(
                mf6_river_aquifer_flux
            )[:]
        )

    def store_1d_river_fluxes_to_dfm(self) -> None:
        """
        Stores current contents of fluxes going into dflowfm
        (dfm in this instance) through qext
        """
        #       self.dflow1d_flux_estimate = np.copy(self.dfm.get_1d_river_fluxes())
        dfm_estimate = self.dfm.get_1d_river_fluxes()
        if dfm_estimate is not None:
            self.dflow1d_flux_estimate = dfm_estimate[:]

    def exchange_V_dash_1D(self) -> None:
        """
        From DFM to MF6
        the drainage/inflitration flux to the 1d rivers as realised by DFM is passed to
        mf6 as a correction
        """
        qmf6 = self.mf6.get_river_flux(
            self.coupling.mf6_model, self.coupling.mf6_river_pkg
        )  # originally sent by modflow
        dflow1d_flux_receive = self.dfm.get_1d_river_fluxes()
        if dflow1d_flux_receive is None:
            raise ValueError("dflow 1d river flux not found")
        qdfm = self.dflow1d_flux_estimate
        qmf_corr = calc_correction(
            self.map_active_mod_dflow1d["mf-riv2dflow1d_flux"],
            qmf6,
            qdfm,
            dflow1d_flux_receive,
        )

        assert self.coupling.mf6_msw_well_pkg
        self.mf6.set_correction_flux(
            self.coupling.mf6_model, self.coupling.mf6_wel_correction_pkg, qmf_corr
        )

    def exchange_msw2mod(self) -> None:
        """
        Exchange from Metaswap to MF6

        1- Change of storage-coefficient from MetaSWAP to MF6
        2- Recharge from MetaSWAP to MF6
        3- Sprinkling request from MetaSWAP to MF6

        """
        self.mf6_storage[:] = (
            self.mask_msw2mod["storage"][:] * self.mf6_storage[:]
            + self.map_msw2mod["storage"].dot(self.msw_storage)[:]
        )

        # Divide recharge and extraction by delta time
        tled = 1 / self.delt
        self.mf6_recharge[:] = (
            self.mask_msw2mod["recharge"][:] * self.mf6_recharge[:]
            + tled * self.map_msw2mod["recharge"].dot(self.msw_volume)[:]
        )

        if self.coupling.enable_sprinkling:
            self.mf6_sprinkling_wells[:] = (
                self.mask_msw2mod["sprinkling"][:] * self.mf6_sprinkling_wells[:]
                + tled * self.map_msw2mod["sprinkling"].dot(self.msw_volume)[:]
            )

    def exchange_mod2msw(self) -> None:
        """
        Exchange from MF6 to Metaswap

        1- Exchange of head from MF6 to MetaSWAP
        """
        self.msw_head[:] = (
            self.mask_mod2msw["head"][:] * self.msw_head[:]
            + self.map_mod2msw["head"].dot(self.mf6_head)[:]
        )

    def report_timing_totals(self) -> None:
        total_mf6 = self.mf6.report_timing_totals()
        total_msw = self.msw.report_timing_totals()
        total = total_mf6 + total_msw
        logger.info(f"Total elapsed time in numerical kernels: {total:0.4f} seconds")

    def do_iter_mf_msw(self, sol_id: int) -> bool:
        """Execute a single iteration"""
        self.msw.prepare_solve(0)
        self.msw.solve(0)
        self.exchange_msw2mod()
        has_converged = self.mf6.solve(sol_id)
        self.exchange_mod2msw()
        self.msw.finalize_solve(0)
        return has_converged


def days_to_seconds(time: float) -> float:
    return time * 86400
