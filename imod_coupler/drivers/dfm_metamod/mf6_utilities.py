import numpy as np
from numpy.typing import NDArray
from xmipy import XmiWrapper


class MF6Utilities:
    @classmethod
    def set_river_stages(
        cls,
        mf6_wrapper: XmiWrapper,
        mf6_flowmodel_key: str,
        mf6_river_pkg_key: str,
        new_river_stages: NDArray[np.float_],
    ) -> None:
        """
        sets the river stages in a modflow simulation to the provided values.
        """
        bound_adress = mf6_wrapper.get_var_address(
            "BOUND", mf6_flowmodel_key, mf6_river_pkg_key
        )
        bound = mf6_wrapper.get_value_ptr(bound_adress)
        stage = bound[:, 0]
        if len(new_river_stages) != len(stage):
            raise ValueError(f"Expected size of new_river_stages is {len(stage)}")
        stage[:] = new_river_stages[:]
