from collections.abc import Sequence
from pathlib import Path
from typing import Any

import tomli_w
from imod.mf6 import Modflow6Simulation
from imod.mf6.utilities.regrid import RegridderWeightsCache
from imod.msw import MetaSwapModel
from imod.typing.grid import GridDataArray

from primod.coupled_model import CoupledModel
from primod.driver_coupling.metamod import MetaModDriverCoupling


class MetaMod(CoupledModel):
    """Couple MetaSWAP and MODFLOW 6.

    Parameters
    ----------
    msw_model : MetaSwapModel
        The MetaSWAP model that should be coupled.
    mf6_simulation : Modflow6Simulation
        The Modflow6 simulation that should be coupled.
    """

    _toml_name = "imod_coupler.toml"
    _modflow6_model_dir = "modflow6"
    _metaswap_model_dir = "metaswap"

    def __init__(
        self,
        msw_model: MetaSwapModel,
        mf6_simulation: Modflow6Simulation,
        coupling_list: Sequence[MetaModDriverCoupling],
    ):
        self.msw_model = msw_model
        self.mf6_simulation = mf6_simulation
        self.coupling_list = coupling_list

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
        coupling_dict = self.write_exchanges(directory)
        self.write_toml(
            directory,
            modflow6_dll,
            metaswap_dll,
            metaswap_dll_dependency,
            coupling_dict,
        )

        # Write models
        # For some reason the Modflow 6 model has to be written first, before
        # writing the MetaSWAP model. Else we get an Access Violation Error when
        # running the coupler.
        self.mf6_simulation.write(
            directory / self._modflow6_model_dir,
            **modflow6_write_kwargs,
        )
        self.msw_model.write(directory / self._metaswap_model_dir)

    def write_toml(
        self,
        directory: str | Path,
        modflow6_dll: str | Path,
        metaswap_dll: str | Path,
        metaswap_dll_dependency: str | Path,
        coupling_dict: dict[str, Any],
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
                    "metaswap": {
                        "dll": str(metaswap_dll),
                        "work_dir": f".\\{self._metaswap_model_dir}",
                        "dll_dep_dir": str(metaswap_dll_dependency),
                    },
                },
                "coupling": [coupling_dict],
            },
        }

        with open(toml_path, "wb") as f:
            tomli_w.dump(coupler_toml, f)

        return

    def regrid_like(self, new_grid: GridDataArray) -> "MetaMod":
        regridded_mf6_simulation = self.mf6_simulation.regrid_like(
            "regridded", new_grid, True
        )
        models = regridded_mf6_simulation.get_models()
        dis = list(models.values())[0]["dis"]
        regrid_context = RegridderWeightsCache()
        regridded_msw = self.msw_model.regrid_like(dis, True, regrid_context)

        regridded_metamod = MetaMod(
            msw_model=regridded_msw,
            mf6_simulation=regridded_mf6_simulation,
            coupling_list=self.coupling_list,
        )

        return regridded_metamod
