from pathlib import Path
from typing import Any, Union

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

    def get_recharge(
        self, mf6_flowmodel_key: str, mf6_msw_recharge_pkg: str
    ) -> NDArray[np.float_]:
        mf6_recharge_tag = self.get_var_address(
            "BOUND", mf6_flowmodel_key, mf6_msw_recharge_pkg
        )
        mf6_recharge = self.get_value_ptr(mf6_recharge_tag)[:, 0]
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
        bound_adress = self.get_var_address("BOUND", mf6_flowmodel_key, mf6_package_key)
        bound = self.get_value_ptr(bound_adress)
        bound[:, 0] = new_river_stages[:]

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
        bound_adress = self.get_var_address("BOUND", mf6_flowmodel_key, mf6_package_key)
        bound = self.get_value_ptr(bound_adress)
        stage = bound[:, 0]
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
        bound_adress = self.get_var_address("BOUND", mf6_flowmodel_key, mf6_package_key)
        bound = self.get_value_ptr(bound_adress)
        bot = bound[:, 2]
        return bot

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
        bound_adress = self.get_var_address("BOUND", mf6_flowmodel_key, mf6_wel_pkg_key)
        mf6_flux = self.get_value_ptr(bound_adress)

        if len(assigned_flux) != len(mf6_flux):
            raise ValueError(f"Expected size of flux is {len(mf6_flux)}")
        for i in range(len(assigned_flux)):
            mf6_flux[i, 0] = assigned_flux[i]

        self.set_value(bound_adress, mf6_flux)

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
        bound_adress = self.get_var_address(
            "BOUND", mf6_flowmodel_key, mf6_river_pkg_key
        )
        bound = self.get_value_ptr(bound_adress)

        head_adress = self.get_var_address("X", mf6_flowmodel_key)
        head = self.get_value_ptr(head_adress)
        nodelist_adress = self.get_var_address(
            "NODELIST", mf6_flowmodel_key, mf6_river_pkg_key
        )
        nodelist = self.get_value_ptr(nodelist_adress)

        subset_head = head[nodelist - 1]
        bot = bound[:, 2]
        river_head = np.maximum(subset_head, bot)
        q = NDArray[np.float_](len(nodelist))
        q[:] = bound[:, 1] * (bound[:, 0] - river_head)

        return q

    def get_river_drain_flux(
        self,
        mf6_flowmodel_key: str,
        mf6_river2_drain_pkg_key: str,
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

        rhs_adress = self.get_var_address(
            "RHS", mf6_flowmodel_key, mf6_river2_drain_pkg_key
        )
        package_rhs = self.get_value_ptr(rhs_adress)
        hcof_adress = self.get_var_address(
            "HCOF", mf6_flowmodel_key, mf6_river2_drain_pkg_key
        )
        package_hcof = self.get_value_ptr(hcof_adress)
        head_adress = self.get_var_address("X", mf6_flowmodel_key)
        head = self.get_value_ptr(head_adress)
        package_nodelist_adress = self.get_var_address(
            "NODELIST", mf6_flowmodel_key, mf6_river2_drain_pkg_key
        )
        package_nodelist = self.get_value_ptr(package_nodelist_adress)
        subset_head = head[package_nodelist - 1]

        q = NDArray[np.float_](len(package_nodelist))
        q = package_hcof * subset_head - package_rhs

        return q
