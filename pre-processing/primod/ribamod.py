from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import ribasim
import tomli_w
import xarray as xr
from imod.mf6 import Drainage, GroundwaterFlowModel, Modflow6Simulation, River
from numpy.typing import NDArray

from primod.driver_coupling.ribamod import RibaModDriverCoupling
from primod.typing import Int


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
        coupling_list: list[RibaModDriverCoupling],
    ):
        self.validate_time_window(
            ribasim_model=ribasim_model,
            mf6_simulation=mf6_simulation,
        )
        self.ribasim_model = ribasim_model
        self.mf6_simulation = mf6_simulation
        self.coupling_list = coupling_list

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

    def _nullify_ribasim_exchange_input(
        self, coupled_basin_node_ids: NDArray[Int]
    ) -> None:
        """
        Set the input forcing to NoData for drainage and infiltration.

        Ribasim will otherwise overwrite the values set by the coupler.
        """

        # FUTURE: in coupling to MetaSWAP, the runoff should be set nodata as well.
        def _nullify(df: pd.DataFrame) -> None:
            """Set drainage and infiltration columns to nodata if present in df"""
            if df is not None:
                columns_present = list(
                    {"drainage", "infiltration"}.intersection(df.columns)
                )
                if len(columns_present) > 0:
                    df.loc[
                        df["node_id"].isin(coupled_basin_node_ids), columns_present
                    ] = np.nan
            return

        basin = self.ribasim_model.basin
        _nullify(basin.static.df)
        _nullify(basin.time.df)
        return

    def write_exchanges(
        self,
        directory: str | Path,
    ) -> tuple[dict[str, dict[str, str]], NDArray[Int]]:
        """
        Write exchanges and return their filenames for the coupler
        configuration file.

        Also return the coupled basins for Ribasim: for these basins, the
        drainage and infiltration has to nullified.
        """
        # Assume only one groundwater flow model
        # FUTURE: Support multiple groundwater flow models.
        gwf_model = self.mf6_simulation[gwf_names[0]]

        exchange_dir = Path(directory) / "exchanges"
        exchange_dir.mkdir(exist_ok=True, parents=True)

        coupled_node_indices = []
        list_of_mapping_dicts = []
        mf6_models = []
        for coupling in self.coupling_list:
            mf6_models.append(coupling.mf6_model)
            mapping_dict, basin_node_indices = coupling.process(self)
                ribasim_model=self.ribasim_model,
                gwf_model=gwf_model,
            )
            coupled_node_indices.append(basin_node_indices)
            list_of_mapping_dicts.append(mapping_dict)

        # FUTURE: if we support multiple MF6 models, group them by name before
        # merging, and return a list of coupling_dicts.
        merged_coupling_dict = self.coupling_list[0]._empty_coupling_dict()
        merged_coupling_dict["mf6_model"] = mf6_models[0]
        for mapping_dict in list_of_mapping_dicts:
            for destination, mappings in mapping_dict.items():
                for mapping in mappings:
                    filename = mapping.write(directory)
                    merged_coupling_dict[destination][mapping.name] = filename

        coupled_basin_node_ids = np.unique(np.concatenate(coupled_node_indices))
        return merged_coupling_dict, coupled_basin_node_ids
