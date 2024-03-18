from pathlib import Path
from typing import Any

import tomli_w
from imod.mf6 import Modflow6Simulation
from imod.mf6.model import Modflow6Model
from imod.msw import GridData, MetaSwapModel, Sprinkling

from primod.driver_coupling.metamod import MetaModDriverCoupling
from primod.mapping.node_svat_mapping import NodeSvatMapping
from primod.mapping.rch_svat_mapping import RechargeSvatMapping
from primod.mapping.wel_svat_mapping import WellSvatMapping


class MetaMod:
    """Couple MetaSWAP and MODFLOW 6.

    Parameters
    ----------
    msw_model : MetaSwapModel
        The MetaSWAP model that should be coupled.
    mf6_simulation : Modflow6Simulation
        The Modflow6 simulation that should be coupled.
    mf6_rch_pkgkey: str
        Key of Modflow 6 recharge package to which MetaSWAP is coupled.
    mf6_wel_pkgkey: str or None
        Optional key of Modflow 6 well package to which MetaSWAP sprinkling is
        coupled.
    """

    _toml_name = "imod_coupler.toml"
    _modflow6_model_dir = "Modflow6"
    _metaswap_model_dir = "MetaSWAP"

    def __init__(
        self,
        msw_model: MetaSwapModel,
        mf6_simulation: Modflow6Simulation,
        coupling_list: list[MetaModDriverCoupling],
    ):
        self.msw_model = msw_model
        self.mf6_simulation = mf6_simulation
        self.coupling_list = coupling_list
        self.is_sprinkling = self._check_coupler_and_sprinkling()

    def _check_coupler_and_sprinkling(self) -> bool:
        driver_coupling = self.coupling_list[0]
        mf6_rch_pkgkey = driver_coupling.recharge_package
        mf6_wel_pkgkey = driver_coupling.wel_package

        gwf_names = self._get_gwf_modelnames()

        # Assume only one groundwater flow model
        # FUTURE: Support multiple groundwater flow models.
        gwf_model = self.mf6_simulation[gwf_names[0]]

        if mf6_rch_pkgkey not in gwf_model.keys():
            raise ValueError(
                f"No package named {mf6_rch_pkgkey} detected in Modflow 6 model. "
                "iMOD_coupler requires a Recharge package."
            )

        sprinkling_key = self.msw_model._get_pkg_key(Sprinkling, optional_package=True)

        sprinkling_in_msw = sprinkling_key is not None
        sprinkling_in_mf6 = mf6_wel_pkgkey in gwf_model.keys()

        if sprinkling_in_msw and not sprinkling_in_mf6:
            raise ValueError(
                f"No package named {mf6_wel_pkgkey} found in Modflow 6 model, "
                "but Sprinkling package found in MetaSWAP. "
                "iMOD Coupler requires a Well Package "
                "to couple wells."
            )
        elif not sprinkling_in_msw and sprinkling_in_mf6:
            raise ValueError(
                f"Modflow 6 Well package {mf6_wel_pkgkey} specified for sprinkling, "
                "but no Sprinkling package found in MetaSWAP model."
            )
        elif sprinkling_in_msw and sprinkling_in_mf6:
            return True
        else:
            return False

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
        # For some reason the Modflow 6 model has to be written first, before
        # writing the MetaSWAP model. Else we get an Access Violation Error when
        # running the coupler.
        self.mf6_simulation.write(
            directory / self._modflow6_model_dir,
            **modflow6_write_kwargs,
        )
        self.msw_model.write(directory / self._metaswap_model_dir)

        # Write exchange files
        exchange_dir = directory / "exchanges"
        exchange_dir.mkdir(mode=755, exist_ok=True)
        coupling_dict = self.write_exchanges(exchange_dir)

        self.write_toml(
            directory,
            modflow6_dll,
            metaswap_dll,
            metaswap_dll_dependency,
            coupling_dict,
        )

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

    def _get_gwf_modelnames(self, mf6_simulation) -> list[str]:
        """
        Get names of gwf models in mf6 simulation
        """
        return [
            key
            for key, value in mf6_simulation.items()
            if isinstance(value, Modflow6Model)
        ]

    def write_exchanges(
        self,
        directory: str | Path,
    ) -> dict[str, Any]:
        """
        Write exchange files (.dxc) which map MetaSWAP's svats to Modflow 6 node
        numbers, recharge ids, and well ids.

        Parameters
        ----------
        directory: str or Path
            Directory where .dxc files are written.
        mf6_rch_pkgkey: str
            Key of Modflow 6 recharge package to which MetaSWAP is coupled.
        mf6_wel_pkgkey: str
            Key of Modflow 6 well package to which MetaSWAP sprinkling is
            coupled.
        """
        coupling = self.coupling_list[0]
        coupling_dict = coupling.write_exchanges(
            directory=directory, coupled_model=self
        )
        return coupling_dict
