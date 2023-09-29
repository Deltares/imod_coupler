from pathlib import Path
from typing import Union

import numpy as np
from numpy.typing import NDArray
from xmipy import XmiWrapper


class SwapWrapper(XmiWrapper):
    def __init__(
        self,
        lib_path: Union[str, Path],
        lib_dependency: Union[str, Path, None] = None,
        working_directory: Union[str, Path, None] = None,
        timing: bool = False,
    ):
        super().__init__(lib_path, lib_dependency, working_directory, timing)

    def get_head_ptr(self) -> NDArray[np.float_]:
        """
        Gets heads array from metaswap

        Parameters
        ----------
        none

        Returns
        -------
         msw_head: NDArray[np.float_]
            array of the heads used by metaswap. Array as pointer to the MetaSWAP intenal array
        """
        return self.get_value_ptr("dhgwmod")

    def get_volume_ptr(self) -> NDArray[np.float_]:
        """
        Gets volume array from metaswap

        Parameters
        ----------
        none

        Returns
        -------
         msw_volume: NDArray[np.float_]
            array of volume used by metaswap. Array as pointer to the MetaSWAP intenal array
        """
        return self.get_value_ptr("dvsim")

    def get_storage_ptr(self) -> NDArray[np.float_]:
        """
        Gets storage array from metaswap

        Parameters
        ----------
        none

        Returns
        -------
         msw_storage: NDArray[np.float_]
            array of storage used by metaswap. Array as pointer to the MetaSWAP intenal array
        """
        return self.get_value_ptr("dsc1sim")
