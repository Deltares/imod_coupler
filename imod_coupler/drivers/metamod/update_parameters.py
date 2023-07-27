from pathlib import Path
from typing import Any, Dict

import numpy as np

from imod_coupler.drivers.metamod.save_and_restore import save_and_restore_state
from imod_coupler.kernelwrappers.mf6_wrapper import Mf6Wrapper


class mf6_update_parameters:
    array_pointers: Dict[str, np.ndarray[Any, Any]]
    nnodes: int

    def __init__(
        self,
        mf6: Mf6Wrapper,
        mf6_model_name: str,
        list_packages: Dict[str, list[str]],
        arrays_dir: Path,
        save_and_restore: save_and_restore_state,
    ) -> None:
        self.mf6 = mf6
        self.mf6_model_name = mf6_model_name.upper()
        self.list_packages = list_packages
        self.arrays_dir = arrays_dir
        self.save_and_restore = save_and_restore
        self._set_array_pointers()
        self._init_clases()

    def update(self) -> None:
        local_time = self.save_and_restore.local_time()
        irepeat = self.save_and_restore.repeat
        if local_time == 1 and irepeat != 0 and "npf" in self.list_packages.keys():
            self.npf.update_condsat(irepeat)

    def _init_clases(self) -> None:
        if "npf" in self.list_packages.keys():
            self.npf = update_npf(
                self.arrays_dir,
                self.array_pointers,
                self.nnodes,
            )

    def _get_pointer_adreses(self) -> dict[str, str]:
        TAGS = {
            "npf": [
                "CON/IA",
                "CON/JA",
                "CON/IHC",
                "DIS/TOP",
                "DIS/BOT",
                "DIS/DELR",
                "DIS/DELC",
                "DIS/IDOMAIN",
                "NPF/CONDSAT",
                "NPF/K11",
                "NPF/K22",
                "NPF/K33",
            ],
            "riv": [
                "BOUND/{name}",
                "DIS/TOP",
            ],
        }
        pointer_adreses = {}
        for _, package_names in self.list_packages.items():
            for package_name in package_names:
                array_tags = TAGS[package_name]
                for array_tag in array_tags:
                    package_adres, package_array = array_tag.split("/")
                    package_array = package_array.format(name=package_name)
                    if package_array not in pointer_adreses:
                        pointer_adreses[package_array] = self.mf6.get_var_address(
                            package_array, self.mf6_model_name, package_adres
                        )
        return pointer_adreses

    def _set_array_pointers(self) -> None:
        pointer_adreses = self._get_pointer_adreses()
        self.array_pointers = {}
        for name, adres in pointer_adreses.items():
            self.array_pointers[name.lower()] = self.mf6.get_value_ptr(adres)
        self.nnodes = self.array_pointers["top"].shape[0]
        self.array_pointers["active"] = self.array_pointers["idomain"].flatten() > 0
        self._checks()

    def _checks(
        self,
    ) -> None:
        if self.array_pointers["delr"].max() != self.array_pointers["delc"].max():
            raise Exception("delr != delc is not supported")
        dif = np.diff(self.array_pointers["delr"].flatten())
        if any(dif != dif[0]):
            raise Exception("only equidistant grids supported")
        if any(self.array_pointers["ihc"] == 2):
            raise Exception("staggered horizontal connections not supported")
        if any(self.array_pointers["k11"] != self.array_pointers["k22"]):
            raise Exception("only isotropic kh supported")


class update_npf:
    other_contributions_condsat: np.ndarray[Any, Any]

    def __init__(
        self,
        arrays_dir: Path,
        array_pointers: dict[str, np.ndarray[Any, Any]],
        nnodes: int,
    ) -> None:
        self.arrays_dir = arrays_dir
        self.array_pointers = array_pointers
        self.nnodes = nnodes
        self._set_other_contributions_condsat()

    def _get_upper_diagonal_indexes(
        self,
    ) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any]]:
        n = np.diff(np.copy(self.array_pointers["ia"]))
        ii = np.repeat(np.arange(self.nnodes) + 1, n)
        jj = np.copy(self.array_pointers["ja"])
        # upper diagonal + 0 based
        return ii[jj > ii] - 1, jj[jj > ii] - 1

    def update_condsat(self, itime: float) -> None:
        # get arrays; possible only kh or only kv
        kh_file = self.arrays_dir / "npf" / "kh_{time}".format(time=int(itime))
        kh_ok = kh_file.is_file()
        kv_file = self.arrays_dir / "npf" / "kv_{time}".format(time=int(itime))
        kv_ok = kv_file.is_file()
        if not kh_ok and not kv_ok:
            raise Exception("not files found for update of npf-package")
        condsat_new = np.zeros(
            self.array_pointers["condsat"].shape,
            dtype=np.float64,
        )
        if kh_ok:
            kh = np.fromfile(kh_file, dtype=np.float64)
            condsat_new = self._update_lateral_cond(condsat_new, kh)
        elif not kh_ok:
            # we update condsat, k11 keeps the original kh values
            condsat_new = self._update_lateral_cond(
                condsat_new, self.array_pointers["k11"]
            )
        if kv_ok:
            kv = np.fromfile(kv_file, dtype=self.array_pointers["condsat"].dtype)
            condsat_new = self._update_vertical_cond(condsat_new, kv)
        elif not kv_ok:
            # we update condsat, k33 keeps the original kv values
            condsat_new = self._update_vertical_cond(
                condsat_new, self.array_pointers["k33"]
            )
        self.array_pointers["condsat"][:] = (
            condsat_new + self.other_contributions_condsat
        )

    def _set_other_contributions_condsat(self) -> None:
        """use function once before first update of condsat"""
        condsat_from_k = np.zeros(self.array_pointers["condsat"].shape)
        condsat_from_k = self._update_lateral_cond(
            condsat_from_k, self.array_pointers["k11"]
        )
        condsat_from_k = self._update_vertical_cond(
            condsat_from_k, self.array_pointers["k33"]
        )
        self.other_contributions_condsat = (
            self.array_pointers["condsat"] - condsat_from_k
        )

    def _update_lateral_cond(
        self, condsat_new: np.ndarray[Any, Any], kh: np.ndarray[Any, Any]
    ) -> np.ndarray[Any, Any]:
        i, j = self._get_upper_diagonal_indexes()
        i, j = (
            i[self.array_pointers["ihc"] == 1],
            j[self.array_pointers["ihc"] == 1],
        )
        thicknes = self.array_pointers["top"] - self.array_pointers["bot"]

        Tnm = kh[self.array_pointers["active"]][i] * thicknes[i]
        Tmn = kh[self.array_pointers["active"]][j] * thicknes[j]
        Lnm = self.array_pointers["delr"][0] / 2
        Lmn = self.array_pointers["delr"][0] / 2
        condsat_index = np.arange(self.array_pointers["condsat"].shape[0])[
            self.array_pointers["ihc"] == 1
        ]
        condsat_new[condsat_index] = self.array_pointers["delr"][0] * (
            (Tnm * Tmn) / ((Tnm * Lmn) + (Tmn * Lnm))
        )
        return condsat_new

    def _update_vertical_cond(
        self, condsat_new: np.ndarray[Any, Any], kv: np.ndarray[Any, Any]
    ) -> np.ndarray[Any, Any]:
        i, j = self._get_upper_diagonal_indexes()
        i, j = (
            i[self.array_pointers["ihc"] == 0],
            j[self.array_pointers["ihc"] == 0],
        )
        thicknes = self.array_pointers["top"] - self.array_pointers["bot"]
        Tnm = kv[self.array_pointers["active"]][i] * self.array_pointers["delr"][0]
        Tmn = kv[self.array_pointers["active"]][j] * self.array_pointers["delr"][0]
        Lnm = thicknes[i] / 2
        Lmn = thicknes[j] / 2
        condsat_index = np.arange(self.array_pointers["condsat"].shape[0])[
            self.array_pointers["ihc"] == 0
        ]
        condsat_new[condsat_index] = self.array_pointers["delr"][0] * (
            (Tnm * Tmn) / ((Tnm * Lmn) + (Tmn * Lnm))
        )
        return condsat_new
