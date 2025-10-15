from ctypes import byref, c_int, create_string_buffer
from typing import Any

import numpy as np
from numpy.typing import NDArray
from xmipy import XmiWrapper


class RibasimWrapper(XmiWrapper):
    drainage_infiltration: NDArray[np.float64]
    drainage: NDArray[np.float64]
    infiltration: NDArray[np.float64]
    _julia_initialised: bool = False

    def initialize(self, config_file: str = "") -> None:
        super().initialize(config_file)
        self.set_infiltration_drainage_array()

    def finalize(self) -> None:
        super().finalize()
        self.finalize_julia()

    def initialize_julia(self) -> None:
        if not RibasimWrapper._julia_initialised:
            argument = create_string_buffer(0)
            self.lib.init_julia(c_int(0), byref(argument))
            RibasimWrapper._julia_initialised = True

    def finalize_julia(self) -> None:
        if RibasimWrapper._julia_initialised:
            self.lib.shutdown_julia(c_int(0))
            RibasimWrapper._julia_initialised = False

    def get_constant_int(self, name: str) -> int:
        match name:
            case "BMI_LENVARTYPE":
                return 51
            case "BMI_LENGRIDTYPE":
                return 17
            case "BMI_LENVARADDRESS":
                return 68
            case "BMI_LENCOMPONENTNAME":
                return 256
            case "BMI_LENVERSION":
                return 256
            case "BMI_LENERRMESSAGE":
                return 1025
        raise ValueError(f"{name} does not map to an integer exposed by Ribasim")

    def update_subgrid_level(self) -> None:
        self.lib.update_subgrid_level()

    def execute(self, config_file: str) -> None:
        self._execute_function(self.lib.execute, config_file.encode())

    def set_infiltration_drainage_array(self) -> None:
        self.infiltration = self.get_value_ptr("basin.infiltration")
        self.drainage = self.get_value_ptr("basin.drainage")
        self.drainage_infiltration = np.zeros_like(self.infiltration)
        self.cumulative_infiltration = self.get_value_ptr(
            "basin.cumulative_infiltration"
        )
        self.infiltration_save = np.empty_like(self.cumulative_infiltration)
        self.cumulative_drainage = self.get_value_ptr("basin.cumulative_drainage")
        self.drainage_save = np.empty_like(self.cumulative_drainage)

    def set_water_user_arrays(self) -> None:
        self.user_demand = self.get_value_ptr("user_demand.demand")
        self.user_realized_cumulative = self.get_value_ptr(
            "user_demand.cumulative_inflow"
        )
        self.user_realized_fraction = np.zeros_like(self.user_realized_cumulative)
        n_users = self.user_realized_cumulative.size
        n_priorities = self.user_demand.size // n_users
        self.user_demand.resize(n_priorities, n_users)
        self.user_demand_flat = np.zeros(n_users, dtype=np.float64)
        self.user_realized_saved = np.copy(self.user_realized_cumulative)

    def set_coupled_user(self, coupled_user_mask: NDArray[np.int32]) -> None:
        self.coupled_user_indices = np.flatnonzero(coupled_user_mask == 0)
        self.coupled_priority_indices, _ = np.nonzero(
            self.user_demand[:, self.coupled_user_indices]
        )
        # check for multiple priorities per user
        unique, counts = np.unique(self.coupled_user_indices, return_counts=True)
        too_many = unique[counts > 1] + 1
        if np.size(too_many) > 0:
            raise ValueError(
                f"More than one priority set for sprinkling user demands {too_many}."
            )
        # zero all coupled demand elements
        self.user_demand[self.coupled_priority_indices, self.coupled_user_indices] = 0.0

    def exchange_demand_water_users(self) -> None:
        self.user_demand[self.coupled_priority_indices, self.coupled_user_indices] = (
            self.user_demand_flat[self.coupled_user_indices]
        )

    def set_realised_fraction_water_users(self, delt: float) -> None:
        self.user_realized_fraction[:] = 0.0
        nonzero = np.flatnonzero(self.user_demand_flat)
        self.user_realized_fraction[nonzero] = (
            (self.user_realized_cumulative[nonzero] - self.user_realized_saved[nonzero])
            / delt
        ) / self.user_demand_flat[nonzero]
        self.user_realized_saved[:] = self.user_realized_cumulative[:]

    def exchange_infiltration_drainage(self, coupled_index: NDArray[np.int32]) -> None:
        self.infiltration[coupled_index] = np.where(
            self.drainage_infiltration < 0, -self.drainage_infiltration, 0
        )[coupled_index]
        self.drainage[coupled_index] = np.where(
            self.drainage_infiltration > 0, self.drainage_infiltration, 0
        )[coupled_index]

    def compute_realized_drainage_infiltration(self) -> Any:
        return (self.cumulative_drainage[:] - self.drainage_save[:]) - (
            self.cumulative_infiltration[:] - self.infiltration_save[:]
        )

    def save_cumulative_drainage_infiltration(self) -> None:
        self.infiltration_save[:] = self.cumulative_infiltration[:]
        self.drainage_save[:] = self.cumulative_drainage[:]
