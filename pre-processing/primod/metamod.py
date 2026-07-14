import shutil
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import tomli_w
from imod.mf6 import Modflow6Simulation
from imod.msw import MetaSwapModel

from primod.coupled_model import CoupledModel
from primod.driver_coupling.metamod import MetaModDriverCoupling
from primod.model_mixin import MetaModMixin


class MetaMod(CoupledModel, MetaModMixin):
    """Couple MetaSWAP and MODFLOW 6.

    Parameters
    ----------
    msw_model : MetaSwapModel
        The MetaSWAP model that should be coupled.
    mf6_simulation : Modflow6Simulation
        The Modflow6 simulation that should be coupled.
    coupling_list: list of DriverCoupling
        One entry per MODFLOW 6 model that should be coupled
    """

    _toml_name = "imod_coupler.toml"
    _modflow6_model_dir = "modflow6"
    _metaswap_model_dir = "metaswap"

    def __init__(
        self,
        msw_model: dict[str, MetaSwapModel] | MetaSwapModel,
        mf6_simulation: Modflow6Simulation,
        coupling_list: Sequence[MetaModDriverCoupling],
    ):
        self.mf6_simulation = mf6_simulation
        self.coupling_list = coupling_list
        if isinstance(msw_model, MetaSwapModel):
            self.msw_model = {"MSW": msw_model}
            self.coupling_list[0].msw_model = "MSW"
        else:
            self.msw_model = msw_model
        self.newton_formulation = self.coupling_list[0].has_newton_formulation(
            self.mf6_simulation
        )

    def write(
        self,
        directory: str | Path,
        modflow6_dll: str | Path,
        metaswap_dll: str | Path,
        metaswap_dll_dependency: str | Path,
        modflow6_write_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """
        Write MetaSWAP and Modflow 6 model with exchange files, as well as a
        ``.toml`` file which configures the imod coupler run.

        Parameters
        ----------
        directory: str or Path
            Directory in which to write the coupled models
        modflow6_dll: str or Path
            Path to modflow6 .dll. You can obtain this library by downloading
            `the last iMOD5 release
            <https://oss.deltares.nl/web/imod/download-imod5>`_
        metaswap_dll: str or Path
            Path to metaswap .dll. You can obtain this library by downloading
            `the last iMOD5 release
            <https://oss.deltares.nl/web/imod/download-imod5>`_
        metaswap_dll_dependency: str or Path
            Directory with metaswap .dll dependencies. Directory should contain:
            [fmpich2.dll, mpich2mpi.dll, mpich2nemesis.dll, TRANSOL.dll]. You
            can obtain these by downloading `the last iMOD5 release
            <https://oss.deltares.nl/web/imod/download-imod5>`_
        modflow6_write_kwargs: dict
            Optional dictionary with keyword arguments for the writing of
            Modflow6 models. You can use this for example to turn off the
            validation at writing (``validation=False``) or to write text files
            (``binary=False``)
        """

        if modflow6_write_kwargs is None:
            modflow6_write_kwargs = {}

        # force to Path
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        # Write exchange files
        coupling_dict_list = self.write_exchanges(directory)
        self.write_toml(
            directory,
            modflow6_dll,
            metaswap_dll,
            metaswap_dll_dependency,
            coupling_dict_list,
        )

        # Write models
        # For some reason the Modflow 6 model has to be written first, before
        # writing the MetaSWAP model. Else we get an Access Violation Error when
        # running the coupler.
        self.mf6_simulation.write(
            directory / self._modflow6_model_dir,
            **modflow6_write_kwargs,
        )

        mf6_dis_pkg, mf6_wel_pkg = self.get_mf6_pkgs_for_metaswap(
            coupling_dict_list, self.mf6_simulation
        )

        if isinstance(metaswap_dll, str):
            metaswap_dll_path = Path(metaswap_dll)
        else:
            metaswap_dll_path = metaswap_dll

        for msw_model_key, msw_model in self.msw_model.items():
            directory_msw = directory / self._metaswap_model_dir / Path(msw_model_key)

            # Write the MetaSWAP (sub)models
            msw_model.write(
                directory_msw,
                mf6_dis_pkg[msw_model_key],
                mf6_wel_pkg[msw_model_key],
            )

            # Copy DLLs to MetaSWAP working directory, only when they exist.
            if metaswap_dll_path.is_file():
                dll_path = Path(directory_msw, metaswap_dll_path.name)
                shutil.copy(metaswap_dll, dll_path)
            if metaswap_dll_dependency is not None:
                if isinstance(metaswap_dll_dependency, str):
                    dll_dep_dir_path = Path(metaswap_dll_dependency)
                else:
                    dll_dep_dir_path = metaswap_dll_dependency
                for dep_dll_path in list((dll_dep_dir_path).glob("*")):
                    shutil.copy(dep_dll_path, directory_msw)

    def write_toml(
        self,
        directory: str | Path,
        modflow6_dll: str | Path,
        metaswap_dll: str | Path,
        metaswap_dll_dependency: str | Path,
        coupling_dict_list: list[dict[str, Any]],
    ) -> None:
        """
        Write .toml file which configures the imod coupler run.

        Parameters
        ----------
        directory: str or Path
            Directory in which to write the .toml file.
        modflow6_dll: str or Path
            Path to modflow6 .dll. You can obtain this library by downloading
            `the last iMOD5 release
            <https://oss.deltares.nl/web/imod/download-imod5>`_
        metaswap_dll: str or Path
            Path to metaswap .dll. You can obtain this library by downloading
            `the last iMOD5 release
            <https://oss.deltares.nl/web/imod/download-imod5>`_
        metaswap_dll_dependency: str or Path
            Directory with metaswap .dll dependencies. Directory should contain:
            [fmpich2.dll, mpich2mpi.dll, mpich2nemesis.dll, TRANSOL.dll]. You
            can obtain these by downloading `the last iMOD5 release
            <https://oss.deltares.nl/web/imod/download-imod5>`_
        coupling_dict: dict
            Dictionary with names of coupler packages and paths to mappings.
        """
        # force to Path
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        toml_path = directory / self._toml_name

        # create MetaSWAP dictionary
        msw_dict_list: list[dict[str, Any]] = []
        for msw_model in self.msw_model.keys():
            work_dir = f".\\{self._metaswap_model_dir}\\{msw_model}"
            d = {}
            d["msw_model"] = msw_model
            d["dll"] = f"{work_dir}\\{Path(metaswap_dll).name}"
            d["dll_dep_dir"] = work_dir
            d["work_dir"] = work_dir
            msw_dict_list.append(d)

        msw_dat_toml: dict[str, Any] | list[dict[str, Any]]
        coupling_dat_toml: dict[str, Any] | list[dict[str, Any]]

        if len(msw_dict_list) == 1:
            msw_dat_toml = msw_dict_list[0]
        else:
            msw_dat_toml = msw_dict_list

        if len(coupling_dict_list) == 1:
            coupling_dat_toml = coupling_dict_list[0]
        else:
            coupling_dat_toml = coupling_dict_list

        coupler_toml = {
            "timing": False,
            "log_level": "INFO",
            "driver_type": "metamod",
            "driver": {
                "kernels": {
                    "modflow6": {
                        "dll": str(modflow6_dll),
                        "work_dir": f".\\{self._modflow6_model_dir}",
                    },
                    "metaswap": msw_dat_toml,
                },
                "coupling": coupling_dat_toml,
            },
        }
        if self.newton_formulation:
            coupler_toml["modflow_newton_formulation"] = True

        with open(toml_path, "wb") as f:
            tomli_w.dump(coupler_toml, f)

        return
