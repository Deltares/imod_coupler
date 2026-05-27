from __future__ import annotations

from abc import ABC
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from xmipy import XmiWrapper


class Mf6Wrapper(XmiWrapper):
    packages: dict[str, Mf6River | Mf6Drainage | Mf6Api] = {}
    ats: ATSRetryController

    def __init__(
        self,
        lib_path: str | Path,
        lib_dependency: str | Path | None = None,
        working_directory: str | Path | None = None,
        timing: bool = False,
    ):
        super().__init__(lib_path, lib_dependency, working_directory, timing)

    def get_head(self, mf6_flowmodel_key: str) -> NDArray[np.float64]:
        mf6_head_tag = self.get_var_address("X", mf6_flowmodel_key)
        mf6_head = self.get_value_ptr(mf6_head_tag)
        return mf6_head

    def set_ats_package(self) -> None:
        self.ats = ATSRetryController(self)

    def set_api_packages(
        self, mf6_flowmodel_key: str, mf6_api_keys: Sequence[str]
    ) -> None:
        for mf6_api_key in mf6_api_keys:
            self.packages[mf6_api_key] = Mf6Api(self, mf6_flowmodel_key, mf6_api_key)

    def set_rivers_packages(
        self, mf6_flowmodel_key: str, mf6_river_keys: Sequence[str]
    ) -> None:
        for mf6_river_key in mf6_river_keys:
            self.packages[mf6_river_key] = Mf6River(
                self, mf6_flowmodel_key, mf6_river_key
            )

    def set_drainage_packages(
        self, mf6_flowmodel_key: str, mf6_drainage_keys: Sequence[str]
    ) -> None:
        for mf6_drainage_key in mf6_drainage_keys:
            self.packages[mf6_drainage_key] = Mf6Drainage(
                self, mf6_flowmodel_key, mf6_drainage_key
            )

    def get_well(
        self,
        mf6_flowmodel_key: str,
        mf6_msw_recharge_pkg: str,
    ) -> NDArray[np.float64]:
        wel_tag = self.get_var_address("Q", mf6_flowmodel_key, mf6_msw_recharge_pkg)
        return self.get_value_ptr(wel_tag)

    def get_uzf_infiltration(
        self, mf6_flowmodel_key: str, mf6_uzf_pkg: str
    ) -> NDArray[np.float64]:
        mf6_infiltration_tag = self.get_var_address(
            "SINF_PVAR", mf6_flowmodel_key, mf6_uzf_pkg
        )
        return self.get_value_ptr(mf6_infiltration_tag)

    def get_uzf_nodes(
        self, mf6_flowmodel_key: str, mf6_uzf_pkg: str
    ) -> NDArray[np.float64]:
        mf6_infiltration_tag = self.get_var_address(
            "NODELIST", mf6_flowmodel_key, mf6_uzf_pkg
        )
        return self.get_value_ptr(mf6_infiltration_tag)

    def get_uzf_landflag(
        self, mf6_flowmodel_key: str, mf6_uzf_pkg: str
    ) -> NDArray[np.float64]:
        mf6_infiltration_tag = self.get_var_address(
            "LANDFLAG", mf6_flowmodel_key, mf6_uzf_pkg
        )
        return self.get_value_ptr(mf6_infiltration_tag)

    def get_uzf_top(
        self, mf6_flowmodel_key: str, mf6_uzf_pkg: str
    ) -> NDArray[np.float64]:
        mf6_infiltration_tag = self.get_var_address(
            "CELTOP", mf6_flowmodel_key, mf6_uzf_pkg
        )
        return self.get_value_ptr(mf6_infiltration_tag)

    def get_recharge(
        self,
        mf6_flowmodel_key: str,
        mf6_msw_recharge_pkg: str,
    ) -> NDArray[np.float64]:
        mf6_recharge_tag = self.get_var_address(
            "RECHARGE", mf6_flowmodel_key, mf6_msw_recharge_pkg
        )
        return self.get_value_ptr(mf6_recharge_tag)

    def get_recharge_nodes(
        self,
        mf6_flowmodel_key: str,
        mf6_msw_recharge_pkg: str,
    ) -> NDArray[Any]:
        mf6_recharge_nodes_tag = self.get_var_address(
            "NODELIST", mf6_flowmodel_key, mf6_msw_recharge_pkg
        )
        return self.get_value_ptr(mf6_recharge_nodes_tag)

    def get_storage(self, mf6_flowmodel_key: str) -> NDArray[np.float64]:
        mf6_storage_tag = self.get_var_address("SS", mf6_flowmodel_key, "STO")
        mf6_storage = self.get_value_ptr(mf6_storage_tag)
        return mf6_storage

    def get_area(self, mf6_flowmodel_key: str) -> NDArray[np.float64]:
        mf6_area_tag = self.get_var_address("AREA", mf6_flowmodel_key, "DIS")
        mf6_area = self.get_value_ptr(mf6_area_tag)
        return mf6_area

    def get_top(self, mf6_flowmodel_key: str) -> NDArray[np.float64]:
        mf6_top_tag = self.get_var_address("TOP", mf6_flowmodel_key, "DIS")
        mf6_top = self.get_value_ptr(mf6_top_tag)
        return mf6_top

    def get_bot(self, mf6_flowmodel_key: str) -> NDArray[np.float64]:
        mf6_bot_tag = self.get_var_address("BOT", mf6_flowmodel_key, "DIS")
        mf6_bot = self.get_value_ptr(mf6_bot_tag)
        return mf6_bot

    def max_iter(self) -> Any:
        mf6_max_iter_tag = self.get_var_address("MXITER", "SLN_1")
        mf6_max_iter = self.get_value_ptr(mf6_max_iter_tag)[0]
        return mf6_max_iter

    def get_sprinkling(
        self,
        mf6_flowmodel_key: str,
        mf6_package_key: str,
    ) -> NDArray[np.float64]:
        mf6_sprinkling_tag = self.get_var_address(
            "BOUND", mf6_flowmodel_key, mf6_package_key
        )
        mf6_sprinkling_wells = self.get_value_ptr(mf6_sprinkling_tag)[:, 0]
        return mf6_sprinkling_wells

    def get_ss(self, mf6_flowmodel_key: str) -> NDArray[np.float64]:
        mf6_storage_tag = self.get_var_address("SS", mf6_flowmodel_key, "STO")
        mf6_storage = self.get_value_ptr(mf6_storage_tag)
        return mf6_storage

    def get_sy(self, mf6_flowmodel_key: str) -> NDArray[np.float64]:
        mf6_storage_tag = self.get_var_address("SY", mf6_flowmodel_key, "STO")
        mf6_storage = self.get_value_ptr(mf6_storage_tag)
        return mf6_storage

    def get_dis_shape(self, mf6_flowmodel_key: str) -> tuple[int, int, int]:
        nlay_tag = self.get_var_address("NLAY", mf6_flowmodel_key, "DIS")
        nrow_tag = self.get_var_address("NROW", mf6_flowmodel_key, "DIS")
        ncol_tag = self.get_var_address("NCOL", mf6_flowmodel_key, "DIS")
        return (
            self.get_value_ptr(nlay_tag)[0],
            self.get_value_ptr(nrow_tag)[0],
            self.get_value_ptr(ncol_tag)[0],
        )

    def get_nodeuser(self, mf6_flowmodel_key: str) -> NDArray[np.int32]:
        nodeuser_tag = self.get_var_address("NODEUSER", mf6_flowmodel_key, "DIS")
        return self.get_value_ptr(nodeuser_tag)

    def get_saturation(self, mf6_flowmodel_key: str) -> NDArray[np.float64]:
        saturation_tag = self.get_var_address("SAT", mf6_flowmodel_key, "NPF")
        return self.get_value_ptr(saturation_tag)

    def has_sc1(self, mf6_flowmodel_key: str) -> bool:
        mf6_is_sc1_tag = self.get_var_address("ISTOR_COEF", mf6_flowmodel_key, "STO")
        mf6_has_sc1 = bool(self.get_value_ptr(mf6_is_sc1_tag)[0] != 0)
        return mf6_has_sc1


class Mf6Boundary(ABC):
    nodelist: NDArray[np.int32]
    hcof: NDArray[np.float64]
    rhs: NDArray[np.float64]
    maxbound: NDArray[np.int32]
    nbound: NDArray[np.int32]

    def __init__(
        self, mf6_wrapper: Mf6Wrapper, mf6_flowmodel_key: str, mf6_pkg_key: str
    ):
        self.mf6_wrapper = mf6_wrapper
        nodelist_address = mf6_wrapper.get_var_address(
            "NODELIST",
            mf6_flowmodel_key,
            mf6_pkg_key,
        )
        rhs_address = mf6_wrapper.get_var_address(
            "RHS",
            mf6_flowmodel_key,
            mf6_pkg_key,
        )
        hcof_address = mf6_wrapper.get_var_address(
            "HCOF", mf6_flowmodel_key, mf6_pkg_key
        )
        maxbound_address = mf6_wrapper.get_var_address(
            "MAXBOUND", mf6_flowmodel_key, mf6_pkg_key
        )
        nbound_address = mf6_wrapper.get_var_address(
            "NBOUND", mf6_flowmodel_key, mf6_pkg_key
        )
        # Fortran 1-based versus Python 0-based indexing
        self.nodelist = mf6_wrapper.get_value_ptr(nodelist_address)
        self.rhs = mf6_wrapper.get_value_ptr(rhs_address)
        self.hcof = mf6_wrapper.get_value_ptr(hcof_address)
        self.maxbound = mf6_wrapper.get_value_ptr(maxbound_address)
        self.nbound = mf6_wrapper.get_value_ptr(nbound_address)


class Mf6Api(Mf6Boundary):
    def __init__(
        self, mf6_wrapper: Mf6Wrapper, mf6_flowmodel_key: str, mf6_pkg_key: str
    ):
        super().__init__(mf6_wrapper, mf6_flowmodel_key, mf6_pkg_key)

    def get_flux_estimate(
        self,
        head: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        raise NotImplementedError('API package does not support "get_flux_estimate"')

    def get_flux(
        self,
        head: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        raise NotImplementedError('API package does not support "get_flux"')

    @property
    def n_bound(self) -> int:
        return len(self.rhs)


class Mf6HeadBoundary(Mf6Boundary):
    head: NDArray[np.float64]
    private_nodelist: NDArray[np.int32]

    def __init__(
        self, mf6_wrapper: Mf6Wrapper, mf6_flowmodel_key: str, mf6_pkg_key: str
    ):
        super().__init__(mf6_wrapper, mf6_flowmodel_key, mf6_pkg_key)

        # Fortran 1-based versus Python 0-based indexing
        self.head = np.empty_like(self.hcof)
        self.q = np.empty_like(self.hcof)
        self.q_estimate = np.empty_like(self.hcof)
        self.private_nodelist = (
            self.nodelist - 1
        )  # internal to this class, therefore 0-based

    def set_private_nodelist(self) -> None:
        """
        The nodelist behaves differently than HCOF and RHS.
        While the nodelist can be fetched from MODFLOW 6, this will result in a
        dummy array of only -1 values. Apparently, it is not allocated yet (?)
        and the allocation only occurs after the first prepare_time_step.
        """
        self.private_nodelist = self.nodelist - 1

    @property
    def n_bound(self) -> int:
        return len(self.rhs)

    def get_flux(
        self,
        head: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """
        Returns the calculated river or DRN fluxes of MF6. In MF6 the RIV
        boundary condition is added to the solution in the following matter:

        RHS = -cond*(hriv-rivbot)
        HCOF = -cond

        if head < bot then HCOF = 0

        for the DRN package:

        RHS = -f * cond * bot
        HCOF = -f * cond

        Where f is the 'drainage scaling factor' when using the option 'auxdepthname'.


        The MF6 solutions has the form of:

        A * h = Q

        Therefore, the flux contributions of DRN, GHB, and RIV can be
        calculated by:

        Flux = HCOF * X - RHS


        When this function is called before initialisation of a new timestep
        (t), the calculated flux is of timestep t-1. If function is called
        before initialisation of the first timestep, the calculated flux will
        be zero.

        Parameters
        ----------
        head: NDArray[np.float64]
            The MODFLOW6 head for every cell.

        Returns
        -------
        NDArray[np.float64]
            flux (array size = nr of river nodes)
            sign is positive for infiltration
        """
        # Avoid allocating large arrays
        self.set_private_nodelist()
        self.head[:] = head[self.private_nodelist]
        np.multiply(self.hcof, self.head, out=self.q)
        self.q -= self.rhs
        return self.q


class Mf6River(Mf6HeadBoundary):
    private_nodelist: NDArray[np.int32]
    conductance: NDArray[np.float64]
    bottom_elevation: NDArray[np.float64]
    head: NDArray[np.float64]
    bottom_minimum: NDArray[np.float64]

    def __init__(
        self, mf6_wrapper: Mf6Wrapper, mf6_flowmodel_key: str, mf6_pkg_key: str
    ):
        super().__init__(mf6_wrapper, mf6_flowmodel_key, mf6_pkg_key)

        stage_address = mf6_wrapper.get_var_address(
            "STAGE", mf6_flowmodel_key, mf6_pkg_key
        )
        self.stage = mf6_wrapper.get_value_ptr(stage_address)
        cond_address = mf6_wrapper.get_var_address(
            "COND", mf6_flowmodel_key, mf6_pkg_key
        )
        self.conductance = mf6_wrapper.get_value_ptr(cond_address)
        rbot_address = mf6_wrapper.get_var_address(
            "RBOT", mf6_flowmodel_key, mf6_pkg_key
        )
        self.bottom_elevation = mf6_wrapper.get_value_ptr(rbot_address)
        self.bottom_minimum = self.bottom_elevation.copy()

    def update_bottom_minimum(self) -> None:
        self.bottom_minimum[:] = self.bottom_elevation[:]

    @property
    def water_level(self) -> NDArray[np.float64]:
        return self.stage

    def set_water_level(self, new_water_level: NDArray[np.float64]) -> None:
        np.maximum(self.bottom_minimum, new_water_level, out=self.stage)

    def get_flux_estimate(
        self,
        head: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """
        Returns the river fluxes consistent with current head, river stage and conductance.
        a simple linear model is used: flux[m3/d] = conductance[m2/d] * (stage[m] - max(head[m], bottom[m]))
        Bottom is the level of the river bottom.

        This function does not use the HCOF and RHS for calculating the flux, bacause it is used
        at the beginning of the timestep. At that time
        the package HCOF and RHS are not updated yet by MF6. Therefore we use the bottom level,
        conductance and head of the previous timestep, and the stage of the new timestep.

        Parameters
        ----------
        head: NDArray[np.float64]
            The MODFLOW6 head for every cell.

        Returns
        -------
        NDArray[np.float64]
            flux (array size = nr of river nodes)
            sign is positive for infiltration
        """

        self.set_private_nodelist()
        self.head[:] = head[self.private_nodelist]
        max_head = np.maximum(self.head, self.bottom_elevation)
        np.subtract(self.stage, max_head, out=self.q_estimate)
        np.multiply(self.conductance, self.q_estimate, out=self.q_estimate)
        return self.q_estimate


class Mf6Drainage(Mf6HeadBoundary):
    conductance: NDArray[np.float64]
    elevation: NDArray[np.float64]
    elevation_minimum: NDArray[np.float64]

    def __init__(
        self, mf6_wrapper: Mf6Wrapper, mf6_flowmodel_key: str, mf6_pkg_key: str
    ):
        super().__init__(mf6_wrapper, mf6_flowmodel_key, mf6_pkg_key)
        elev_address = mf6_wrapper.get_var_address(
            "ELEV", mf6_flowmodel_key, mf6_pkg_key
        )
        self.elevation = mf6_wrapper.get_value_ptr(elev_address)
        cond_address = mf6_wrapper.get_var_address(
            "COND", mf6_flowmodel_key, mf6_pkg_key
        )
        self.conductance = mf6_wrapper.get_value_ptr(cond_address)
        self.elevation_minimum = self.elevation.copy()

    def update_bottom_minimum(self) -> None:
        self.elevation_minimum[:] = self.elevation

    @property
    def water_level(self) -> NDArray[np.float64]:
        return self.elevation

    def set_water_level(self, new_water_level: NDArray[np.float64]) -> None:
        np.maximum(self.elevation_minimum, new_water_level, out=self.elevation)

    def get_flux_estimate(
        self,
        head: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """
        Returns the drn fluxes consistent with current head, stage and conductance.
        a simple linear model is used: flux = conductance * (stage - head)

        This function does not use the HCOF and RHS for calculating the flux, bacause it is used
        at the beginning of the timestep. At that time
        the package HCOF and RHS are not updated yet by MF6. Therefore we use conductance and head
        of the previous timestep, and the stage of the new timestep.

        Parameters
        ----------
        head: NDArray[np.float64]
            The MODFLOW6 head for every cell.

        Returns
        -------
        NDArray[np.float64]
            flux (array size = nr of river nodes)
            sign is positive for infiltration
        """
        self.set_private_nodelist()
        self.head[:] = head[self.private_nodelist]
        max_head = np.maximum(self.head, self.elevation)
        np.subtract(self.elevation, max_head, out=self.q_estimate)
        np.multiply(self.conductance, self.q_estimate, out=self.q_estimate)
        return self.q_estimate


"""
ATS retry logic for XMI-based MODFLOW 6 coupling.

The XMI path (prepare_solve -> solve -> finalize_solve) bypasses the
internal retry loop that exists in Mf6DoTimestep(). This module
replicates that retry behavior in Python using BMI memory access to
read ATS parameters and reset delt on non-convergence.

Memory addresses used:
  ATS/KPERATS   - array mapping stress periods to ATS record index (size NPER)
  ATS/DTFAILADJ - failure adjustment factor per ATS record
  ATS/DTMIN     - minimum time step per ATS record
  TDIS/DELT     - current time step size
  TDIS/KPER     - current stress period
  TDIS/KSTP     - current time step number
  SIM/ISIMCNVG  - simulation convergence flag
"""



class ATSRetryController:
    """Implements ATS retry logic for XMI-based MODFLOW 6 coupling.

    """

    def __init__(self, mf6: XmiWrapper):
        """Initialize with a reference to the XMI wrapper.

        Args:
            mf6: XMI wrapper object that provides get_value_ptr()
                 for BMI memory access.
        """
        self.mf6 = mf6

        # Get pointers to ATS arrays
        self.kperats = mf6.get_value_ptr("ATS/KPERATS")  # int array (NPER)
        self.dtfailadj = mf6.get_value_ptr("ATS/DTFAILADJ")  # float array (MAXATS)
        self.dtmin = mf6.get_value_ptr("ATS/DTMIN")  # float array (MAXATS)

        # Get pointers to TDIS scalars
        self.delt = mf6.get_value_ptr("TDIS/DELT")  # float scalar
        self.kper = mf6.get_value_ptr("TDIS/KPER")  # int scalar
        self.kstp = mf6.get_value_ptr("TDIS/KSTP")  # int scalar

        self.totim = self.mf6.get_value_ptr("TDIS/TOTIM")
        self.totimsav = self.mf6.get_value_ptr("TDIS/TOTIMSAV")
        self.pertim = self.mf6.get_value_ptr("TDIS/PERTIM")
        self.pertimsav = self.mf6.get_value_ptr("TDIS/PERTIMSAV")

        # Get pointers to end-of-period/simulation flags and period lengths
        # These are needed by tdis_delt_reset logic
        self.endofperiod = mf6.get_value_ptr("TDIS/ENDOFPERIOD") 
        self.endofsimulation = mf6.get_value_ptr("TDIS/ENDOFSIMULATION")
        self.perlen = mf6.get_value_ptr("TDIS/PERLEN")  # float array (NPER)
        self.nper = mf6.get_value_ptr("TDIS/NPER")  # int scalar
        self.totalsimtime = mf6.get_value_ptr("TDIS/TOTALSIMTIME")  # float scalar
        self.nstp = mf6.get_value_ptr("TDIS/NSTP")  # int array (NPER)

        # Convergence flag for the solution (equivalent to converge_reset)
        self.icnvg = mf6.get_value_ptr("SLN_1/ICNVG")  # int scalar

        # Fortran LOGICAL(4) convention: .TRUE. = -1, .FALSE. = 0
        self.FORTRAN_TRUE = -1
        self.FORTRAN_FALSE = 0

        self._finished_trying = True
        self._retry_count = 0

    def _is_adaptive_period(self) -> bool:
        """Check if current stress period has ATS active."""
        kper = int(self.kper[0])  # 1-based in Fortran
        if kper < 1 or kper > len(self.kperats):
            return False
        return self.kperats[kper - 1] > 0  # 0-based Python index

    def _get_ats_index(self) -> int:
        """Get the ATS record index for the current stress period (0-based)."""
        kper = int(self.kper[0])
        return self.kperats[kper - 1] - 1  # Fortran 1-based -> Python 0-based

    def prepare(self) -> None:
        """Call before the solve loop for each time step."""
        self._finished_trying = True
        self._retry_count = 0

    def should_retry(self) -> bool:
        """Check if the time step should be retried with a smaller delt.

        Replicates the logic in ats_reset_delt() from src/Timing/ats.f90.

        Returns:
            True if a retry should be attempted (delt has been reduced).
            False if giving up (not adaptive, or delt already at minimum).
        """
        if not self._is_adaptive_period():
            return False

        n = self._get_ats_index()
        tsfact = self.dtfailadj[n]

        if tsfact <= 1.0:
            # No failure adjustment configured
            return False

        delt_new = self.delt[0] / tsfact
        kper = int(self.kper[0])
        kstp = int(self.kstp[0])

        if delt_new < self.dtmin[n]:
            # Would go below minimum time step - give up
            print(
                f"  Failed solution for step {kstp} and period {kper} "
                f"new delt of {delt_new:.7E} below minimum of {self.dtmin[n]:.7E}; giving up"
            )
            return False

        # Reduce delt
        self.delt[0] = delt_new
        self._finished_trying = False

        print(
            f"  Failed solution for step {kstp} and period {kper} "
            f"will be retried using time step of {delt_new:.7E}"
        )
        return True

    def retry(self) -> None:
        """Reset MODFLOW state for a retry attempt.

        This replicates what sim_step_retry() does in mf6core.f90:
        1. ats_reset_delt: reduce delt (already done in should_retry)
        2. tdis_delt_reset: update totim, pertim, endofperiod, endofsimulation
        3. converge_reset: reset the simulation convergence flag

        After calling this, the caller should re-run:
          prepare_solve() -> solve() loop -> finalize_solve()
        """
        # The delt was already reduced in should_retry().
        self._retry_count += 1

        # --- Replicate tdis_delt_reset(deltnew) ---
        # Update totim and pertim to match the new (reduced) delt
        self.totim[0] = self.totimsav[0] + self.delt[0]
        self.pertim[0] = self.pertimsav[0] + self.delt[0]

        # Update end-of-period indicator
        kper = int(self.kper[0])  # 1-based
        self.endofperiod[0] = self.FORTRAN_FALSE

        if self._is_adaptive_period():
            # ats_set_endofperiod: end of period when pertim ≈ perlen
            n = self._get_ats_index()
            perlencurrent = self.perlen[kper - 1]
            if abs(self.pertim[0] - perlencurrent) < self.dtmin[n]:
                self.endofperiod[0] = self.FORTRAN_TRUE
        else:
            # Non-adaptive: end of period at last time step
            if int(self.kstp[0]) == self.nstp[kper - 1]:
                self.endofperiod[0] = self.FORTRAN_TRUE

        # Update end-of-simulation indicator
        if self.endofperiod[0] != self.FORTRAN_FALSE and kper == int(self.nper[0]):
            self.endofsimulation[0] = self.FORTRAN_TRUE
            self.totim[0] = self.totalsimtime[0]

        # --- Replicate converge_reset() ---
        # Reset the convergence flag so MODFLOW considers the solution
        # unconverged and models know to restore their state
        self.icnvg[0] = 1