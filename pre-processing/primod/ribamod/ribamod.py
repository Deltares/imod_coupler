from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import geopandas as gpd
import imod
import numpy as np
import pandas as pd
import ribasim
import tomli_w
import xarray as xr
from imod.mf6 import Drainage, GroundwaterFlowModel, Modflow6Simulation, River
from numpy.typing import NDArray

from primod.ribamod.exchange_creator import (
    derive_active_coupling,
    derive_passive_coupling,
)
from primod.typing import Int


@dataclass
class DriverCoupling:
    """A dataclass representing one coupling scenario for the RibaMod driver.

    Attributes
    ----------
    mf6_model : str
        The model of the driver.
    basin_definition : gpd.GeoDataFrame
        GeoDataFrame of basin polygons
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
    basin_definition: gpd.GeoDataFrame
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
    ):
        self.validate_time_window(
            ribasim_model=ribasim_model,
            mf6_simulation=mf6_simulation,
        )
        self.ribasim_model = ribasim_model
        self.mf6_simulation = mf6_simulation
        self.coupling_list = coupling_list

    def _get_gwf_modelnames(self) -> list[str]:
        """
        Get names of gwf models in mf6 simulation
        """
        return [
            key
            for key, value in self.mf6_simulation.items()
            if isinstance(value, GroundwaterFlowModel)
        ]

    @staticmethod
    def _new_coupling_dict() -> dict[str, Any]:
        return {
            "mf6_active_river_packages": {},
            "mf6_passive_river_packages": {},
            "mf6_active_drainage_packages": {},
            "mf6_passive_drainage_packages": {},
        }

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
        coupling_dict, coupled_basins = self.write_exchanges(directory)

        self._nullify_ribasim_exchange_input(coupled_basins)

        self.mf6_simulation.write(
            directory / self._modflow6_model_dir,
            **modflow6_write_kwargs,
        )
        self.ribasim_model.write(directory / self._ribasim_model_dir / "ribasim.toml")
        self.write_toml(
            directory,
            coupling_dict,
            modflow6_dll,
            ribasim_dll,
            ribasim_dll_dependency,
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

    @staticmethod
    def validate_time_window(
        ribasim_model: ribasim.Model,
        mf6_simulation: Modflow6Simulation,
    ) -> None:
        def to_timestamp(xr_time: xr.DataArray) -> pd.Timestamp:
            return pd.Timestamp(xr_time.to_numpy().item())

        mf6_timedis = mf6_simulation["time_discretization"].dataset
        mf6_start = to_timestamp(mf6_timedis["time"].isel(time=0)).to_pydatetime()
        time_delta = pd.to_timedelta(
            mf6_timedis["timestep_duration"].isel(time=-1).item(), unit="days"
        )
        mf6_end = (
            to_timestamp(mf6_timedis["time"].isel(time=-1)) + time_delta
        ).to_pydatetime()

        ribasim_start = ribasim_model.starttime
        ribasim_end = ribasim_model.endtime
        if ribasim_start != mf6_start or ribasim_end != mf6_end:
            raise ValueError(
                "Ribasim simulation time window does not match MODFLOW6.\n"
                f"Ribasim: {ribasim_start} to {ribasim_end}\n"
                f"MODFLOW6: {mf6_start} to {mf6_end}\n"
            )
        return

    def validate_basin_node_ids(self, basin_definition: gpd.GeoDataFrame) -> pd.Series:
        assert self.ribasim_model.basin.profile.df is not None
        basin_ids: NDArray[Int] = np.unique(
            self.ribasim_model.basin.profile.df["node_id"]
        )
        missing = ~np.isin(basin_definition["node_id"], basin_ids)
        if missing.any():
            missing_basins = basin_definition["node_id"].to_numpy()[missing]
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

    def _nullify_ribasim_exchange_input(
        self, coupled_basin_node_ids: NDArray[Int]
    ) -> None:
        """
        Set the input forcing to NoData for drainage and infiltration.

        Ribasim will otherwise overwrite the values set by the coupler.
        """
        # FUTURE: in coupling to MetaSWAP, the runoff should be set nodata as well.
        basin = self.ribasim_model.basin
        if basin.static.df is not None:
            df = basin.static.df
            df.loc[
                df["node_id"].isin(coupled_basin_node_ids), ["drainage", "infiltration"]
            ] = np.nan
        if basin.time.df is not None:
            df = basin.time.df
            df.loc[
                df["node_id"].isin(coupled_basin_node_ids), ["drainage", "infiltration"]
            ] = np.nan
        return

    def _process_driver_coupling(
        self,
        gwf_model: GroundwaterFlowModel,
        coupling: DriverCoupling,
    ) -> tuple[dict[str, Any], list[NDArray[Int]]]:
        dis = gwf_model[gwf_model._get_pkgkey("dis")]
        packages = asdict(coupling)
        packages.pop("mf6_model")
        basin_definition = packages.pop("basin_definition")

        # Validate
        if "node_id" not in basin_definition.columns:
            raise ValueError(
                'Basin definition must contain "node_id" column.'
                f"Columns in dataframe: {basin_definition.columns}"
            )
        # Check whether names in driver_coupling are present in MF6 model.
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

        # Spatial overlays of MF6 boundaries with basin polygons.
        basin_ids = self.validate_basin_node_ids(basin_definition)
        subgrid_df = self.validate_subgrid_df(coupling)
        gridded_basin = imod.prepare.rasterize(
            basin_definition,
            like=dis["idomain"].isel(layer=0, drop=True),
            column="node_id",
        )

        # Collect which Ribasim basins are coupled, so that we can set their
        # drainage and infiltration to NoData later on.
        tables_dict = self._new_coupling_dict()
        coupled_basin_indices = []
        for destination, keys in packages.items():
            for key in keys:
                package = gwf_model[key]
                # Derive exchange tables
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

                if table.empty:
                    raise ValueError(
                        f"No coupling can be derived for MODFLOW 6 package: {key}."
                        "No spatial overlap exists between the basin_definition and this package."
                    )

                tables_dict[destination][key] = table
                coupled_basin_indices.append(table["basin_index"])

        coupled_basin_indices = np.unique(np.concatenate(coupled_basin_indices))
        coupled_basin_node_ids = basin_ids[coupled_basin_indices]
        return tables_dict, coupled_basin_node_ids

    def write_exchanges(
        self,
        directory: str | Path,
    ) -> tuple[dict[str, dict[str, str]], NDArray[Int]]:
        # Assume only one groundwater flow model
        # FUTURE: Support multiple groundwater flow models.
        gwf_names = self._get_gwf_modelnames()
        gwf_model = self.mf6_simulation[gwf_names[0]]

        exchange_dir = Path(directory) / "exchanges"
        exchange_dir.mkdir(exist_ok=True, parents=True)

        coupled_node_indices = []
        list_of_tables_dicts = []
        mf6_models = []
        for coupling in self.coupling_list:
            mf6_models.append(coupling.mf6_model)
            tables_dict, basin_node_indices = self._process_driver_coupling(
                gwf_model=gwf_model,
                coupling=coupling,
            )
            coupled_node_indices.append(basin_node_indices)
            list_of_tables_dicts.append(tables_dict)

        # FUTURE: if we support multiple MF6 models, group them by name before
        # merging, and return a list of coupling_dicts.
        merged_coupling_dict = self._new_coupling_dict()
        merged_coupling_dict["mf6_model"] = mf6_models[0]
        for coupling_dict in list_of_tables_dicts:
            for destination, tables in coupling_dict.items():
                for key, table in tables.items():
                    # Write exchange table to TSV file.
                    table.to_csv(exchange_dir / f"{key}.tsv", sep="\t", index=False)
                    # Store path to TSV file for config.
                    merged_coupling_dict[destination][key] = f"exchanges/{key}.tsv"

        coupled_basin_node_ids = np.unique(np.concatenate(coupled_node_indices))
        return merged_coupling_dict, coupled_basin_node_ids
