import os
from pathlib import Path
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
        mf6_workdir: Path,
        original_periods: float,
    ) -> None:
        self.mf6 = mf6
        self.msw = msw
        self.mf6_save_restore_packages = mf6_save_restore_packages(
            mf6=mf6,
            mf6_flowmodel_key=mf6_flowmodel_key,
            mf6_packages=mf6_packages,
            mf6_workdir=mf6_workdir,
        )
        self.mf6_flowmodel_key = mf6_flowmodel_key
        self.local_periods = original_periods
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
    dir: Path

    def __init__(
        self,
        mf6: Mf6Wrapper,
        mf6_flowmodel_key: str,
        mf6_packages: list[str],
        mf6_workdir: Path,
    ) -> None:
        self.mf6 = mf6
        self.last_array = {}
        self.time_array = {}
        self.array_pointers = {}
        self._get_array_pointers(mf6_packages, mf6_flowmodel_key)
        self.mf6_workdir = mf6_workdir
        self._create_dir()

    def save_packages(self, time: float, local_periods: float) -> None:
        for tag, array_pointer in self.array_pointers.items():
            self._save(array_pointer, tag, time, local_periods)

    def restore_packages(
        self, time: float, local_periods: float, local_time: float
    ) -> None:
        for tag, array_pointer in self.array_pointers.items():
            self._restore(array_pointer, tag, time, local_periods, local_time)

    def _get_array_pointers(self, packages: list[str], mf6_flowmodel_key: str) -> None:
        for name in packages:
            tag = self.mf6.get_var_address("BOUND", mf6_flowmodel_key, name.upper())
            array_pointer = self.mf6.get_value_ptr(tag)
            self.array_pointers[tag] = array_pointer

    def _create_dir(self) -> None:
        self.dir = (
            Path(os.getcwd()) / self.mf6_workdir / "save_and_restore_package_arrays"
        )
        os.makedirs(self.dir)

    def _save_array(self, array: NDArray[Any], tag: str, time: float = 1) -> None:
        path = self.dir / (tag.replace("/", "-") + str(int(time)))
        array.tofile(path, sep="")

    def _read_array(self, tag: str, time: float) -> NDArray[Any]:
        path = self.dir / (tag.replace("/", "-") + str(int(time)))
        return np.fromfile(path, dtype=self.last_array[tag].dtype).reshape(
            self.last_array[tag].shape
        )

    def _save(
        self, pointer_array: NDArray[Any], tag: str, time: float, local_periods: float
    ) -> None:
        if time <= local_periods:
            if time == 1.0:
                self.last_array[tag] = np.copy(pointer_array)
                self.time_array[tag] = []
            equal = np.array_equal(self.last_array[tag], pointer_array)
            if not equal:
                first_time = len(self.time_array[tag]) == 0
                if first_time:
                    self._save_array(self.last_array[tag], tag)
                    self._save_array(pointer_array, tag, time)
                    self.time_array[tag].append(1.0)
                    self.time_array[tag].append(time)
                    self.last_array[tag] = np.copy(pointer_array)
                else:
                    self._save_array(self.last_array[tag], tag, time)
                    self.time_array[tag].append(time)
                    self.last_array[tag] = np.copy(pointer_array)

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


def update_tdis(mf6_work_dir: Path, n_repeat: int, tdis_template: str) -> int:
    tdis_template_file = Path(os.getcwd()) / mf6_work_dir / tdis_template
    tdis_file = (
        Path(os.getcwd()) / mf6_work_dir / tdis_template.replace("_template.", ".")
    )
    with open(tdis_template_file, "r") as fin:
        lines = fin.readlines()
    i = -1
    for line in lines:
        i += 1
        if "NPER" in line.upper():
            nper = int(line.split()[1])
            iper = i
        if "BEGIN PERIODDATA" in line.upper():
            istart = i + 1
        if "END PERIODDATA" in line.upper():
            iend = i
    lines[iper] = " NPER " + str(nper * n_repeat) + "\n"
    with open(tdis_file, "w") as fuit:
        fuit.writelines(lines[0:istart])
        fuit.writelines(lines[istart:iend] * n_repeat)
        fuit.writelines(["END PERIODDATA"])
    return nper
