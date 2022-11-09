from typing import Optional

import numpy as np
from numpy.typing import NDArray
from xmipy import XmiWrapper


class Mf6Wrapper(XmiWrapper):
    def set_river_stages(
        self,
        mf6_flowmodel_key: str,
        mf6_river_pkg_key: str,
        new_river_stages: Optional[NDArray[np.float_]],
    ) -> None:
        """
        sets the river stages in a modflow simulation to the provided values.

        Parameters
        ----------
        mf6_flowmodel_key : str
            key of the modflow model
        mf6_river_pkg_key : str
            key of the river package
        new_river_stages : NDArray[np.float_]
            river stages to be set to modflow


        Raises
        ------
        ValueError
            the size of the provided stage array does not match the expected size
        """
        stage = self.get_river_stages(mf6_flowmodel_key, mf6_river_pkg_key)
        if new_river_stages is None or len(new_river_stages) != len(stage):
            raise ValueError(f"Expected size of new_river_stages is {len(stage)}")
        stage[:] = new_river_stages[:]

    def get_river_stages(
        self,
        mf6_flowmodel_key: str,
        mf6_river_pkg_key: str,
    ) -> NDArray[np.float_]:
        bound_adress = self.get_var_address(
            "BOUND", mf6_flowmodel_key, mf6_river_pkg_key
        )
        bound = self.get_value_ptr(bound_adress)
        stage = bound[:, 0]
        return stage

    def get_river_flux(
        self,
        mf6_flowmodel_key: str,
        mf6_river_pkg_key: str,
    ) -> NDArray[np.float_]:
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
