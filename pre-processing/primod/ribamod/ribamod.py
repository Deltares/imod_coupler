from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import geopandas as gpd
import imod
import numpy as np
import pandas as pd
import ribasim
import tomli_w
from imod.mf6 import Drainage, GroundwaterFlowModel, Modflow6Simulation, River

from primod.ribamod.exchange_creator import (
    derive_active_coupling,
    derive_passive_coupling,
)


@dataclass
class DriverCoupling:
    """A dataclass representing one coupling scenario for the RibaMod driver.

    Attributes
    ----------
    mf6_model : str
        The model of the driver.
    mf6_active_river_packages : list of str
        A list of active river packages.
    mf6_passive_river_packages : list of str
        A list of passive river packages.
    mf6_active_drainage_packages : list of str
        A list of active drainage packages.
    mf6_passive_drainage_packages : list of str
        A list of passive drainage packages.
    """

    mf6_model: str
    mf6_active_river_packages: list[str] = field(default_factory=list)
    mf6_passive_river_packages: list[str] = field(default_factory=list)
    mf6_active_drainage_packages: list[str] = field(default_factory=list)
    mf6_passive_drainage_packages: list[str] = field(default_factory=list)


class RibaMod:
    """Couple Ribasim and MODFLOW 6.

    Parameters
    ----------
    ribasim_model : ribasim.model
        The Ribasim model that should be coupled.
    mf6_simulation : Modflow6Simulation
        The Modflow6 simulation that should be coupled.
    coupling_list: list of DriverCoupling
        One entry per MODFLOW 6 model that should be coupled
    """

    _toml_name = "imod_coupler.toml"
    _ribasim_model_dir = "ribasim"
    _modflow6_model_dir = "modflow6"

    def __init__(
        self,
        ribasim_model: ribasim.Model,
        mf6_simulation: Modflow6Simulation,
        coupling_list: list[DriverCoupling],
        basin_definition: gpd.GeoDataFrame,
    ):
        self.ribasim_model = ribasim_model
        self.mf6_simulation = mf6_simulation
        self.coupling_list = coupling_list
        if "node_id" not in basin_definition.columns:
            raise ValueError('Basin definition must contain "node_id" column')
        self.basin_definition = basin_definition

    def _get_gwf_modelnames(self) -> list[str]:
        """
        Get names of gwf models in mf6 simulation
        """
        return [
            key
            for key, value in self.mf6_simulation.items()
            if isinstance(value, GroundwaterFlowModel)
        ]

    def write(
        self,
        directory: str | Path,
        modflow6_dll: str | Path,
        ribasim_dll: str | Path,
        ribasim_dll_dependency: str | Path,
        modflow6_write_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """
        Write Ribasim and Modflow 6 model with exchange files, as well as a
        ``.toml`` file which configures the iMOD Coupler run.

        Parameters
        ----------
        directory: str or Path
            Directory in which to write the coupled models
        modflow6_dll: str or Path
            Path to modflow6 .dll. You can obtain this library by downloading
            `the last iMOD5 release
            <https://oss.deltares.nl/web/imod/download-imod5>`_
        ribasim_dll: str or Path
            Path to ribasim .dll.
        ribasim_dll_dependency: str or Path
            Directory with ribasim .dll dependencies.
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
        self.mf6_simulation.write(
            directory / self._modflow6_model_dir,
            **modflow6_write_kwargs,
        )
        self.ribasim_model.write(directory / self._ribasim_model_dir / "ribasim.toml")
        coupling_dict = self.write_exchanges(directory)
        self.write_toml(
            directory, coupling_dict, modflow6_dll, ribasim_dll, ribasim_dll_dependency
        )

    def write_toml(
        self,
        directory: str | Path,
        coupling_dict: dict[str, Any],
        modflow6_dll: str | Path,
        ribasim_dll: str | Path,
        ribasim_dll_dependency: str | Path,
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
        ribasim_dll: str or Path
            Path to ribasim .dll.
        ribasim_dll_dependency: str or Path
            Directory with ribasim .dll dependencies.
        """
        # force to Path
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)

        toml_path = directory / self._toml_name
        coupler_toml = {
            "timing": False,
            "log_level": "INFO",
            "driver_type": "ribamod",
            "driver": {
                "kernels": {
                    "modflow6": {
                        "dll": str(modflow6_dll),
                        "work_dir": self._modflow6_model_dir,
                    },
                    "ribasim": {
                        "dll": str(ribasim_dll),
                        "dll_dep_dir": str(ribasim_dll_dependency),
                        "config_file": str(
                            Path(self._ribasim_model_dir) / "ribasim.toml"
                        ),
                    },
                },
                "coupling": [coupling_dict],
            },
        }

        with open(toml_path, "wb") as f:
            tomli_w.dump(coupler_toml, f)

    @staticmethod
    def validate_keys(
        gwf_model: GroundwaterFlowModel,
        active_keys: list[str],
        passive_keys: list[str],
        expected_type: River | Drainage,
    ) -> None:
        active_keys_set = set(active_keys)
        passive_keys_set = set(passive_keys)
        intersection = active_keys_set.intersection(passive_keys_set)
        if intersection:
            raise ValueError(f"active and passive keys share members: {intersection}")
        present = [k for k, v in gwf_model.items() if isinstance(v, expected_type)]
        missing = (active_keys_set | passive_keys_set).difference(present)
        if missing:
            raise ValueError(
                f"keys with expected type {expected_type.__name__} are not "
                f"present in the model: {missing}"
            )

    def validate_basin_node_ids(self) -> pd.Series:
        assert self.ribasim_model.basin.profile.df is not None
        basin_ids = np.unique(self.ribasim_model.basin.profile.df["node_id"])
        missing = ~np.isin(self.basin_definition["node_id"], basin_ids)
        if missing.any():
            missing_basins = self.basin_definition["node_id"].to_numpy()[missing]
            raise ValueError(
                "The node IDs of these basins in the basin definition do not "
                f"occur in the Ribasim model: {missing_basins}"
            )
        return basin_ids

    def validate_subgrid_df(self, coupling: DriverCoupling) -> pd.DataFrame | None:
        if coupling.mf6_active_river_packages or coupling.mf6_active_drainage_packages:
            if self.ribasim_model.basin.subgrid.df is None:
                raise ValueError(
                    "ribasim.model.basin.subgrid must be defined for actively coupled packages."
                )
            return self.ribasim_model.basin.subgrid.df
        else:
            return None

    def write_exchanges(
        self,
        directory: str | Path,
    ) -> dict[str, dict[str, str]]:
        gwf_names = self._get_gwf_modelnames()
        # #FUTURE: multiple couplings
        coupling = self.coupling_list[0]

        # Assume only one groundwater flow model
        # FUTURE: Support multiple groundwater flow models.
        gwf_model = self.mf6_simulation[gwf_names[0]]
        self.validate_keys(
            gwf_model,
            coupling.mf6_active_river_packages,
            coupling.mf6_passive_river_packages,
            River,
        )
        self.validate_keys(
            gwf_model,
            coupling.mf6_active_drainage_packages,
            coupling.mf6_passive_drainage_packages,
            Drainage,
        )
        dis = gwf_model[gwf_model._get_pkgkey("dis")]

        basin_ids = self.validate_basin_node_ids()
        subgrid_df = self.validate_subgrid_df(coupling)
        gridded_basin = imod.prepare.rasterize(
            self.basin_definition,
            like=dis["idomain"].isel(layer=0, drop=True),
            column="node_id",
        )

        exchange_dir = Path(directory) / "exchanges"
        exchange_dir.mkdir(exist_ok=True, parents=True)

        packages = asdict(coupling)
        coupling_dict: dict[str, Any] = {destination: {} for destination in packages}
        coupling_dict["mf6_model"] = packages.pop("mf6_model")
        for destination, keys in packages.items():
            for key in keys:
                package = gwf_model[key]
                if "active" in destination:
                    table = derive_active_coupling(
                        gridded_basin=gridded_basin,
                        basin_ids=basin_ids,
                        conductance=package["conductance"],
                        subgrid_df=subgrid_df,
                    )
                else:
                    table = derive_passive_coupling(
                        gridded_basin=gridded_basin,
                        basin_ids=basin_ids,
                        conductance=package["conductance"],
                    )
                table.to_csv(exchange_dir / f"{key}.tsv", sep="\t", index=False)
                coupling_dict[destination][key] = f"exchanges/{key}.tsv"

        return coupling_dict
