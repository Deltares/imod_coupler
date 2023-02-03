from pathlib import Path
from typing import Any, Optional, Union

import numpy as np
from numpy.typing import NDArray
from xmipy import XmiWrapper


class Mf6Wrapper(XmiWrapper):
    def __init__(
        self,
        coupling: Any,
        lib_path: Union[str, Path],
        lib_dependency: Union[str, Path, None] = None,
        working_directory: Union[str, Path, None] = None,
        timing: bool = False,
    ):
        super().__init__(lib_path, lib_dependency, working_directory, timing)
        self.coupling = coupling
        self.mf6_flowmodel_key = self.coupling.mf6_model
        self.mf6_riv1_key = self.coupling.mf6_river_pkg
        self.mf6_riv1_correction_key = self.coupling.mf6_wel_correction_pkg
        self.mf6_msw_recharge_pkg = self.coupling.mf6_msw_recharge_pkg

    def head(self) -> NDArray[np.float_]:
        mf6_head_tag = self.get_var_address("X", self.mf6_flowmodel_key)
        mf6_head = self.get_value_ptr(mf6_head_tag)
        return mf6_head

    def recharge(self) -> NDArray[np.float_]:
        mf6_recharge_tag = self.get_var_address(
            "BOUND", self.mf6_flowmodel_key, self.mf6_msw_recharge_pkg
        )
        mf6_recharge = self.get_value_ptr(mf6_recharge_tag)[:, 0]
        return mf6_recharge

    def storage(self) -> NDArray[np.float_]:
        mf6_storage_tag = self.get_var_address("SS", self.mf6_flowmodel_key, "STO")
        mf6_storage = self.get_value_ptr(mf6_storage_tag)
        return mf6_storage

    def has_sc1(self) -> bool:
        mf6_is_sc1_tag = self.get_var_address(
            "ISTOR_COEF", self.mf6_flowmodel_key, "STO"
        )
        mf6_has_sc1 = bool(self.get_value_ptr(mf6_is_sc1_tag)[0] != 0)
        return mf6_has_sc1

    def area(self) -> NDArray[np.float_]:
        mf6_area_tag = self.get_var_address("AREA", self.mf6_flowmodel_key, "DIS")
        mf6_area = self.get_value_ptr(mf6_area_tag)
        return mf6_area

    def top(self) -> NDArray[np.float_]:
        mf6_top_tag = self.get_var_address("TOP", self.mf6_flowmodel_key, "DIS")
        mf6_top = self.get_value_ptr(mf6_top_tag)
        return mf6_top

    def bot(self) -> NDArray[np.float_]:
        mf6_bot_tag = self.get_var_address("BOT", self.mf6_flowmodel_key, "DIS")
        mf6_bot = self.get_value_ptr(mf6_bot_tag)
        return mf6_bot

    def max_iter(self) -> Any:
        mf6_max_iter_tag = self.get_var_address("MXITER", "SLN_1")
        mf6_max_iter = self.get_value_ptr(mf6_max_iter_tag)[0]
        return mf6_max_iter

    def sprinkling(
        self,
        mf6_package_key: str,
    ) -> NDArray[np.float_]:
        mf6_sprinkling_tag = self.mf6.get_var_address(
            "BOUND", self.mf6_flowmodel_key, mf6_package_key
        )
        mf6_sprinkling_wells = self.get_value_ptr(mf6_sprinkling_tag)[:, 0]
        return mf6_sprinkling_wells

    def set_river_stages(
        self,
        new_river_stages: Optional[NDArray[np.float_]],
    ) -> None:
        """
        sets the river stages in a modflow simulation to the provided values.

        Parameters
        ----------
        new_river_stages : NDArray[np.float_]
            river stages to be set to modflow


        Raises
        ------
        ValueError
            the size of the provided stage array does not match the expected size
        """
        stage = self.get_river_stages()
        if new_river_stages is None or len(new_river_stages) != len(stage):
            raise ValueError(f"Expected size of new_river_stages is {len(stage)}")
        bound_adress = self.get_var_address(
            "BOUND", self.mf6_flowmodel_key, self.mf6_riv1_key
        )
        bound = self.get_value_ptr(bound_adress)
        bound[:, 0] = new_river_stages[:]

    def get_river_stages(self) -> NDArray[np.float_]:
        """returns the river stages of the modflow model

        Parameters
        ----------
        mf6_flowmodel_key : str
            flowmodel key
        mf6_river_pkg_key : str
            river package key

        Returns
        -------
         NDArray[np.float_]:
            stages of the rivers in modflow
        """
        bound_adress = self.get_var_address(
            "BOUND", self.mf6_flowmodel_key, self.mf6_riv1_key
        )
        bound = self.get_value_ptr(bound_adress)
        stage = bound[:, 0]
        return stage

    def get_river_flux(self) -> NDArray[np.float_]:
        """
        returns the river fluxes consistent with current river head, river stage and conductance.
        a simple linear model is used: flux = conductance * (stage - max(head, bot))
        Bot is the levelof the bottom of the river.

        Parameters
        ----------
        mf6_flowmodel_key : str
            name of mf6 groundwater flow model
        mf6_river_pkg_key : str
            name of river package

        Returns
        -------
        NDArray[np.float_]
            flux (array size = nr of river nodes)
            sign is positive for infiltration
        """
        bound_adress = self.get_var_address(
            "BOUND", self.mf6_flowmodel_key, self.mf6_riv1_key
        )
        bound = self.get_value_ptr(bound_adress)

        head_adress = self.get_var_address("X", self.mf6_flowmodel_key)
        head = self.get_value_ptr(head_adress)
        nodelist_adress = self.get_var_address(
            "NODELIST", self.mf6_flowmodel_key, self.mf6_riv1_key
        )
        nodelist = self.get_value_ptr(nodelist_adress)

        subset_head = head[nodelist - 1]
        bot = bound[:, 2]
        river_head = np.maximum(subset_head, bot)
        q = NDArray[np.float_](len(nodelist))
        q[:] = bound[:, 1] * (bound[:, 0] - river_head)

        return q

    def set_correction_flux(
        self,
        correction_flux: Optional[NDArray[np.float_]],
    ) -> None:
        """
        sets the river correction flux in a modflow simulation via the well package

        Parameters
        ----------
        mf6_flowmodel_key : str
            key of the modflow model
        mf6_wel_pkg_key : str
            key of the wel package used for the correction flux
        correction_flux : NDArray[np.float_]
            correction flux to be set to modflow


        Raises
        ------
        ValueError
            the size of the provided flux array does not match the expected size
        """
        bound_adress = self.get_var_address(
            "BOUND", self.mf6_flowmodel_key, self.mf6_riv1_correction_key
        )
        flux = self.get_value_ptr(bound_adress)

        if correction_flux is None or len(correction_flux) != len(flux):
            raise ValueError(f"Expected size of correction_flux is {len(flux)}")
        for i in range(len(flux)):
            flux[i, 0] = correction_flux[i]

        self.set_value(bound_adress, flux)
