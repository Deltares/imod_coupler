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
        bound_adress = self.get_var_address(
            "BOUND", mf6_flowmodel_key, mf6_river_pkg_key
        )
        bound = self.get_value_ptr(bound_adress)
        stage = bound[:, 0]
        if new_river_stages is None or len(new_river_stages) != len(stage):
            raise ValueError(f"Expected size of new_river_stages is {len(stage)}")
        stage[:] = new_river_stages[:]
        self.set_value(bound_adress, stage)

    def set_correction_flux(
        self,
        mf6_flowmodel_key: str,
        mf6_wel_pkg_key: str,
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
        bound_adress = self.get_var_address("BOUND", mf6_flowmodel_key, mf6_wel_pkg_key)
        bound = self.get_value_ptr(bound_adress)
        flux = bound[:, 0]
        if correction_flux is None or len(correction_flux) != len(flux):
            raise ValueError(f"Expected size of new_river_stages is {len(flux)}")
        flux[:] = correction_flux[:]
        self.set_value(bound_adress, flux)
