from abc import ABC
from pathlib import Path
from typing import Any, Dict, Sequence, Union

import numpy as np
from numpy.typing import NDArray
from xmipy import XmiWrapper


class Mf6Wrapper(XmiWrapper):
    def __init__(
        self,
        lib_path: Union[str, Path],
        lib_dependency: Union[str, Path, None] = None,
        working_directory: Union[str, Path, None] = None,
        timing: bool = False,
    ):
        super().__init__(lib_path, lib_dependency, working_directory, timing)

    def get_head(self, mf6_flowmodel_key: str) -> NDArray[np.float_]:
        mf6_head_tag = self.get_var_address("X", mf6_flowmodel_key)
        mf6_head = self.get_value_ptr(mf6_head_tag)
        return mf6_head

    def get_rivers_packages(
        self, mf6_flowmodel_key: str, mf6_river_keys: Sequence[str]
    ) -> Dict[str, "Mf6River"]:
        return {key: Mf6River(self, mf6_flowmodel_key, key) for key in mf6_river_keys}

    def get_drainage_packages(
        self, mf6_flowmodel_key: str, mf6_drainage_keys: Sequence[str]
    ) -> Dict[str, "Mf6Drainage"]:
        return {
            key: Mf6Drainage(self, mf6_flowmodel_key, key) for key in mf6_drainage_keys
        }

    def get_recharge(
        self,
        mf6_flowmodel_key: str,
        mf6_msw_recharge_pkg: str,
        include_nodes: bool = False,
    ) -> Union[NDArray[np.float_], tuple(NDArray[np.float_], NDArray[np.int_])]:
        mf6_recharge_tag = self.get_var_address(
            "RECHARGE", mf6_flowmodel_key, mf6_msw_recharge_pkg
        )
        mf6_recharge = self.get_value_ptr(mf6_recharge_tag)
        mf6_recharge_nodes_tag = self.get_var_address(
            "NODELIST", mf6_flowmodel_key, mf6_msw_recharge_pkg
        )
        mf6_recharge_nodes = self.mf6.get_value_ptr(mf6_recharge_nodes_tag)
        if include_nodes:
            return mf6_recharge, mf6_recharge_nodes
        else:
            return mf6_recharge

    def get_storage(self, mf6_flowmodel_key: str) -> NDArray[np.float_]:
        mf6_storage_tag = self.get_var_address("SS", mf6_flowmodel_key, "STO")
        mf6_storage = self.get_value_ptr(mf6_storage_tag)
        return mf6_storage

    def has_sc1(self, mf6_flowmodel_key: str) -> bool:
        mf6_is_sc1_tag = self.get_var_address("ISTOR_COEF", mf6_flowmodel_key, "STO")
        mf6_has_sc1 = bool(self.get_value_ptr(mf6_is_sc1_tag)[0] != 0)
        return mf6_has_sc1

    def get_area(self, mf6_flowmodel_key: str) -> NDArray[np.float_]:
        mf6_area_tag = self.get_var_address("AREA", mf6_flowmodel_key, "DIS")
        mf6_area = self.get_value_ptr(mf6_area_tag)
        return mf6_area

    def get_top(self, mf6_flowmodel_key: str) -> NDArray[np.float_]:
        mf6_top_tag = self.get_var_address("TOP", mf6_flowmodel_key, "DIS")
        mf6_top = self.get_value_ptr(mf6_top_tag)
        return mf6_top

    def get_bot(self, mf6_flowmodel_key: str) -> NDArray[np.float_]:
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
    ) -> NDArray[np.float_]:
        mf6_sprinkling_tag = self.get_var_address(
            "BOUND", mf6_flowmodel_key, mf6_package_key
        )
        mf6_sprinkling_wells = self.get_value_ptr(mf6_sprinkling_tag)[:, 0]
        return mf6_sprinkling_wells

    def get_drainage_elevation(
        self,
        mf6_flowmodel_key: str,
        mf6_package_key: str,
    ) -> NDArray[np.float64]:
        """
        Returns the drainage elevation of the modflow model

        Parameters
        ----------
        mf6_flowmodel_key : str
            The user-assigned component name of the flow model
        mf6_package_key: str,
            The user-assigned component name of the drainage package

        Returns
        -------
         NDArray[np.float_]:
            Drainage elevation in modflow
        """
        bound_address = self.get_var_address(
            "BOUND", mf6_flowmodel_key, mf6_package_key
        )
        bound = self.get_value_ptr(bound_address)
        stage = bound[:, 0]
        return stage

    def set_drainage_elevation(
        self,
        mf6_flowmodel_key: str,
        mf6_package_key: str,
        new_drainage_elevation: NDArray[np.float_],
    ) -> None:
        """
        Sets the river stages in a modflow simulation to the provided values.

        Parameters
        ----------
        mf6_flowmodel_key: str
            The user-assigned component name of the flow model
        mf6_package_key: str
            The user-assigned component name of the drainage package
        new_drainage_elevation : NDArray[np.float_]
            Drainage elevation to be set to modflow


        Raises
        ------
        ValueError
            the size of the provided stage array does not match the expected size
        """
        stage = self.get_drainage_elevation(mf6_flowmodel_key, mf6_package_key)
        if len(new_drainage_elevation) != len(stage):
            raise ValueError(f"Expected size of new_drainage_elevation is {len(stage)}")
        bound_address = self.get_var_address(
            "BOUND", mf6_flowmodel_key, mf6_package_key
        )
        bound = self.get_value_ptr(bound_address)
        bound[:, 0] = new_drainage_elevation[:]

    def set_river_stages(
        self,
        mf6_flowmodel_key: str,
        mf6_package_key: str,
        new_river_stages: NDArray[np.float_],
    ) -> None:
        """
        Sets the river stages in a modflow simulation to the provided values.

        Parameters
        ----------
        mf6_flowmodel_key: str
            The user-assigned component name of the flow model
        mf6_package_key: str
            The user-assigned component name of the river package
        new_river_stages : NDArray[np.float_]
            river stages to be set to modflow


        Raises
        ------
        ValueError
            the size of the provided stage array does not match the expected size
        """
        stage = self.get_river_stages(mf6_flowmodel_key, mf6_package_key)
        if len(new_river_stages) != len(stage):
            raise ValueError(f"Expected size of new_river_stages is {len(stage)}")
        stage_address = self.get_var_address(
            "STAGE", mf6_flowmodel_key, mf6_package_key
        )
        stage = self.get_value_ptr(stage_address)
        stage[:] = new_river_stages[:]

    def get_river_stages(
        self,
        mf6_flowmodel_key: str,
        mf6_package_key: str,
    ) -> NDArray[np.float64]:
        """
        Returns the river stages of the modflow model

        Parameters
        ----------
        mf6_flowmodel_key : str
            The user-assigned component name of the flow model
        mf6_package_key: str,
            The user-assigned component name of the river package

        Returns
        -------
         NDArray[np.float_]:
            stages of the rivers in modflow
        """
        stage_address = self.get_var_address(
            "STAGE", mf6_flowmodel_key, mf6_package_key
        )
        stage = self.get_value_ptr(stage_address)
        return stage

    def get_river_bot(
        self,
        mf6_flowmodel_key: str,
        mf6_package_key: str,
    ) -> NDArray[np.float64]:
        """
        Returns the river bot of the modflow model

        Parameters
        ----------
        mf6_flowmodel_key : str
            The user-assigned component name of the flow model
        mf6_river_pkg_key : str
            The user-assigned component name of the river package

        Returns
        -------
         NDArray[np.float_]:
            bots of the rivers in modflow
        """
        rbot_address = self.get_var_address("RBOT", mf6_flowmodel_key, mf6_package_key)
        rbot = self.get_value_ptr(rbot_address)
        return rbot

    def set_well_flux(
        self,
        mf6_flowmodel_key: str,
        mf6_wel_pkg_key: str,
        assigned_flux: NDArray[np.float_],
    ) -> None:
        """
        Assigns a flux to the wells in a well package. The number of wells and their order in the mf6 flux array
        should be known beforehand.

        Parameters
        ----------
        mf6_flowmodel_key : str
            The user-assigned component name of the flow model
        mf6_wel_pkg_key : str
            The user-assigned component name of the well package
        assigned_flux : NDArray[np.float_]
            flux to be set to modflow


        Raises
        ------
        ValueError
            the size of the provided flux array does not match the expected size
        """
        bound_address = self.get_var_address(
            "BOUND", mf6_flowmodel_key, mf6_wel_pkg_key
        )
        mf6_flux = self.get_value_ptr(bound_address)

        if len(assigned_flux) != len(mf6_flux):
            raise ValueError(f"Expected size of flux is {len(mf6_flux)}")
        for i in range(len(assigned_flux)):
            mf6_flux[i, 0] = assigned_flux[i]

        self.set_value(bound_address, mf6_flux)

    def get_river_flux_estimate(
        self,
        mf6_flowmodel_key: str,
        mf6_river_pkg_key: str,
    ) -> NDArray[np.float_]:
        """
        Returns the river1 fluxes consistent with current head, river stage and conductance.
        a simple linear model is used: flux = conductance * (stage - max(head, bot))
        Bot is the levelof the bottom of the river.

        This function does not use the HCOF and RHS for calculating the flux, bacause it is used
        at the beginning of the timestep, after updating the river stage by dflow. At that time
        the package HCOF and RHS are not updated yet by MF6. Therefore we use the bottom level,
        conductance and head of the previous timestep, and the stage of the new timestep.

        Parameters
        ----------
        mf6_flowmodel_key : str
            The user-assigned component name of the flow model
        mf6_river_pkg_key : str
            The user-assigned component name of the river package

        Returns
        -------
        NDArray[np.float_]
            flux (array size = nr of river nodes)
            sign is positive for infiltration
        """
        stage_address = self.get_var_address(
            "STAGE", mf6_flowmodel_key, mf6_river_pkg_key
        )
        cond_address = self.get_var_address(
            "COND", mf6_flowmodel_key, mf6_river_pkg_key
        )
        rbot_address = self.get_var_address(
            "RBOT", mf6_flowmodel_key, mf6_river_pkg_key
        )
        stage = self.get_value_ptr(stage_address)
        cond = self.get_value_ptr(cond_address)
        rbot = self.get_value_ptr(rbot_address)

        head_address = self.get_var_address("X", mf6_flowmodel_key)
        head = self.get_value_ptr(head_address)
        nodelist_address = self.get_var_address(
            "NODELIST", mf6_flowmodel_key, mf6_river_pkg_key
        )
        nodelist = self.get_value_ptr(nodelist_address)

        subset_head = head[nodelist - 1]
        river_head = np.maximum(subset_head, rbot)
        q = NDArray[np.float_](len(nodelist))
        q[:] = cond * (stage - river_head)

        return q

    def get_river_drain_flux(
        self,
        mf6_flowmodel_key: str,
        mf6_river_drain_pkg_key: str,
    ) -> NDArray[np.float_]:
        """
        Returns the calculated river or DRN fluxes of MF6. In MF6 the RIV boundary condition is added to the solution in the following matter:

        RHS = -cond*(hriv-rivbot)
        HCOF = -cond

        if head < bot then HCOF = 0

        for the DRN package:

        RHS = -f * cond * bot
        HCOF = -f * cond

        Where f is the 'drainage scaling factor' when using the option 'auxdepthname'.


        The MF6 solutions has the form of:

        A * h = Q

        Therefore, the flux contributions of RIV and DRN can be calculated by:

        Flux = HCOF * X - RHS


        When this function is called before initialisation of a new timestep (t), the
        calculated flux is of timestep t-1. If function is called before initialisation
        of the first timestep, the calculated flux will be zero.

        Parameters
        ----------
        mf6_flowmodel_key : str
            The user-assigned component name of the flow model
        mf6_river_pkg_key : str
            The user-assigned component name of the river or drainage package

        Returns
        -------
        NDArray[np.float_]
            flux (array size = nr of river nodes)
            sign is positive for infiltration
        """

        rhs_address = self.get_var_address(
            "RHS", mf6_flowmodel_key, mf6_river_drain_pkg_key
        )
        package_rhs = self.get_value_ptr(rhs_address)
        hcof_address = self.get_var_address(
            "HCOF", mf6_flowmodel_key, mf6_river_drain_pkg_key
        )
        package_hcof = self.get_value_ptr(hcof_address)
        head_address = self.get_var_address("X", mf6_flowmodel_key)
        head = self.get_value_ptr(head_address)
        package_nodelist_address = self.get_var_address(
            "NODELIST", mf6_flowmodel_key, mf6_river_drain_pkg_key
        )
        package_nodelist = self.get_value_ptr(package_nodelist_address)
        subset_head = head[package_nodelist - 1]

        q = NDArray[np.float_](len(package_nodelist))
        q = package_hcof * subset_head - package_rhs

        return q


class Mf6HeadBoundary(ABC):
    nodelist: NDArray[np.int32]
    hcof: NDArray[np.float64]
    rhs: NDArray[np.float64]
    head: NDArray[np.float64]

    def __init__(
        self, mf6_wrapper: Mf6Wrapper, mf6_flowmodel_key: str, mf6_pkg_key: str
    ):
        self.mf6_wrapper = mf6_wrapper
        self.nodelist_address = mf6_wrapper.get_var_address(
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
        # Fortran 1-based versus Python 0-based indexing
        self.rhs = mf6_wrapper.get_value_ptr(rhs_address)
        self.hcof = mf6_wrapper.get_value_ptr(hcof_address)
        self.head = np.empty_like(self.hcof)
        self.q = np.empty_like(self.hcof)
        return

    @property
    def n_bound(self) -> int:
        return len(self.rhs)

    def get_nodelist(self) -> None:
        """
        The nodelist behaves differently than HCOF and RHS.

        While the nodelist can be fetched from MODFLOW 6, this will result in a
        dummy array of only -1 values. Apparently, it is not allocated yet (?)
        and the allocation only occurs after the first prepare_time_step.
        """
        self.nodelist = self.mf6_wrapper.get_value_ptr(self.nodelist_address) - 1

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
        NDArray[np.float_]
            flux (array size = nr of river nodes)
            sign is positive for infiltration
        """
        # Avoid allocating large arrays
        self.get_nodelist()
        self.head[:] = head[self.nodelist]
        np.multiply(self.hcof, self.head, out=self.q)
        self.q -= self.rhs
        return self.q


class Mf6River(Mf6HeadBoundary):
    nodelist: NDArray[np.int32]
    hcof: NDArray[np.float64]
    rhs: NDArray[np.float64]
    stage: NDArray[np.float64]
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

    def set_stage(self, new_stage: NDArray[np.float64]) -> None:
        np.maximum(self.bottom_minimum, new_stage, out=self.stage)


class Mf6Drainage(Mf6HeadBoundary):
    nodelist: NDArray[np.int32]
    hcof: NDArray[np.float64]
    rhs: NDArray[np.float64]
    conductance: NDArray[np.float64]
    elevation: NDArray[np.float64]
    head: NDArray[np.float64]
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

    def set_elevation(self, new_elevation: NDArray[np.float64]) -> None:
        np.maximum(self.elevation_minimum, new_elevation, out=self.elevation)
