import numpy as np
from numpy.typing import NDArray
from xmipy import XmiWrapper


class MF6_Wrapper(XmiWrapper):
    def set_river_stages(
        self,
        mf6_flowmodel_key: str,
        mf6_river_pkg_key: str,
        new_river_stages: NDArray[np.float_],
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
        if len(new_river_stages) != len(stage):
            raise ValueError(f"Expected size of new_river_stages is {len(stage)}")
        stage[:] = new_river_stages[:]
