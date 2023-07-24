import os
from typing import Any, Dict

import numpy as np
from numpy.typing import NDArray

from imod_coupler.kernelwrappers.mf6_wrapper import Mf6Wrapper
from imod_coupler.kernelwrappers.msw_wrapper import MswWrapper


class save_and_restore_state:
    mf6_saved_hold: NDArray[Any]
    mf6_hold: NDArray[Any]

    def __init__(
        self,
        mf6: Mf6Wrapper,
        msw: MswWrapper,
        mf6_flowmodel_key: str,
        mf6_packages: list[str],
        local_periods: float,
    ) -> None:
        self.mf6 = mf6
        self.msw = msw
        self.mf6_save_restore_packages = mf6_save_restore_packages(
            mf6=mf6, mf6_flowmodel_key=mf6_flowmodel_key, mf6_packages=mf6_packages
        )
        self.mf6_flowmodel_key = mf6_flowmodel_key
        self.local_periods = local_periods
        self._mf6_get_hold_array_pointer(mf6_flowmodel_key)
        self.repeat = 0.0

    def restore_state(self) -> None:
        previous_time = self.time() - self.delta_time()
        local_period = previous_time / (self.local_periods * self.delta_time())
        if local_period.is_integer() and local_period != 0.0:
            self._mf6_restore_hold()
            self._msw_restore_state()

    def save_state(self) -> None:
        if self.time() == 1:
            self._mf6_save_hold()
            self._msw_save_state()

    def mf6_restore_packages(self) -> None:
        self.mf6_save_restore_packages.restore_packages(
            self.time(), self.local_periods, self.local_time()
        )

    def mf6_save_packages(self) -> None:
        self.mf6_save_restore_packages.save_packages(self.time(), self.local_periods)

    def _msw_save_state(self) -> None:
        self.msw.save_state()

    def _msw_restore_state(self) -> None:
        path_org = os.getcwd()
        os.chdir(path_org + "/MetaSWAP")
        self.msw.restore_state()
        os.chdir(path_org)

    def _mf6_save_hold(self) -> None:
        self.mf6_saved_hold = np.copy(self.mf6_hold)

    def _mf6_restore_hold(self) -> None:
        self.mf6_hold[:] = self.mf6_saved_hold[:]

    def _mf6_get_hold_array_pointer(self, mf6_flowmodel_key: str) -> None:
        mf6_hold_tag = self.mf6.get_var_address("XOLD", mf6_flowmodel_key)
        self.mf6_hold = self.mf6.get_value_ptr(mf6_hold_tag)

    def time(self) -> float:
        return self.mf6.get_current_time()

    def end_time(self) -> float:
        return self.mf6.get_end_time()

    def delta_time(self) -> float:
        return self.mf6.get_time_step()

    def local_time(self) -> float:
        previous_time = self.time() - self.delta_time()
        local_period = previous_time / (self.local_periods * self.delta_time())
        if local_period.is_integer() and local_period != 0.0:
            self.repeat = local_period
        return self.time() - (self.local_periods * self.repeat)


class mf6_save_restore_packages:
    last_array: Dict[str, NDArray[Any]]
    time_array: Dict[str, list[float]]
    array_pointers: Dict[str, NDArray[Any]]
    mf6_flowmodel_key: str

    def __init__(
        self,
        mf6: Mf6Wrapper,
        mf6_flowmodel_key: str,
        mf6_packages: list[str],
    ) -> None:
        self.mf6 = mf6
        self.last_array = {}
        self.time_array = {}
        self.array_pointers = {}
        self.get_array_pointers(mf6_packages, mf6_flowmodel_key)

    def save_packages(self, time: float, local_periods: float) -> None:
        for tag, array_pointer in self.array_pointers.items():
            self._save(array_pointer, tag, time, local_periods)

    def restore_packages(
        self, time: float, local_periods: float, local_time: float
    ) -> None:
        for tag, array_pointer in self.array_pointers.items():
            self._restore(array_pointer, tag, time, local_periods, local_time)

    def get_array_pointers(self, packages: list[str], mf6_flowmodel_key: str) -> None:
        for name in packages:
            tag = self.mf6.get_var_address("BOUND", mf6_flowmodel_key, name)
            array_pointer = self.mf6.get_value_ptr(tag)
            self.array_pointers[tag] = array_pointer

    def _save_array(self, array: NDArray[Any], tag: str, time: float = 1) -> None:
        path = os.getcwd() + tag.replace("/", "-") + str(int(time))
        array.tofile(path, sep="")

    def _read_array(self, tag: str, time: float) -> NDArray[Any]:
        path = os.getcwd() + tag.replace("/", "-") + str(int(time))
        return np.fromfile(path).reshape(self.last_array[tag].shape)

    def _save(
        self, pointer_array: NDArray[Any], tag: str, time: float, local_periods: float
    ) -> None:
        if time <= local_periods:
            if time == 1.0:
                self.last_array[tag] = pointer_array.copy()
                self.time_array[tag] = []
            equal = np.array_equal(self.last_array[tag], pointer_array)
            if not equal:
                first_time = len(self.time_array[tag]) == 0
                if first_time:
                    self._save_array(self.last_array[tag], tag)
                    self._save_array(pointer_array, tag, time)
                    self.time_array[tag].append(1.0)
                    self.time_array[tag].append(time)
                    self.last_array[tag] = pointer_array.copy()
                else:
                    self._save_array(self.last_array[tag], tag, time)
                    self.time_array[tag].append(time)
                    self.last_array[tag] = pointer_array.copy()

    def _restore(
        self,
        pointer_array: NDArray[Any],
        tag: str,
        time: float,
        local_periods: float,
        local_time: float,
    ) -> None:
        if time > local_periods:
            if local_time in self.time_array[tag]:
                saved_array = self._read_array(tag, local_time)
                pointer_array[:] = saved_array
