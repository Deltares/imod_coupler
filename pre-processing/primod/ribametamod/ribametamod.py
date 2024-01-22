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
from imod.msw import GridData, MetaSwapModel, Sprinkling
from imod.mf6 import Drainage, GroundwaterFlowModel, Modflow6Simulation, River
from primod.metamod.node_svat_mapping import NodeSvatMapping
from primod.metamod.rch_svat_mapping import RechargeSvatMapping
from primod.metamod.wel_svat_mapping import WellSvatMapping


@dataclass
class DriverCoupling:
    mf6_model: str
    msw_model: str
    mf6_active_river_packages: list[str] = field(default_factory=list)
    mf6_passive_river_packages: list[str] = field(default_factory=list)
    mf6_active_drainage_packages: list[str] = field(default_factory=list)
    mf6_passive_drainage_packages: list[str] = field(default_factory=list)


class RibaMetaMod:
    """
    The RibaMod class creates the necessary input files for coupling Ribasim to
    metaSWAP and MODFLOW 6.

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
    _metaswap_model_dir = "metaswap"

    def __init__(
        self,
        ribasim_model: "ribasim.Model",
        msw_model: MetaSwapModel,
        mf6_simulation: Modflow6Simulation,
        coupling_list: list[DriverCoupling],
        basin_definition: gpd.GeoDataFrame,
        mf6_rch_pkgkey: str,
        mf6_wel_pkgkey: str | None = None,
    ):
        self.ribasim_model = ribasim_model
        self.mf6_simulation = mf6_simulation
        self.msw_model = msw_model
        self.coupling_list = coupling_list
        self.mf6_rch_pkgkey = mf6_rch_pkgkey
        self.mf6_wel_pkgkey = mf6_wel_pkgkey
        self.is_sprinkling = self._check_coupler_and_sprinkling()

        if "node_id" not in basin_definition.columns:
            raise ValueError('Basin definition must contain "node_id" column')
        self.basin_definition = basin_definition

    def _check_coupler_and_sprinkling(self) -> bool:
        mf6_rch_pkgkey = self.mf6_rch_pkgkey
        mf6_wel_pkgkey = self.mf6_wel_pkgkey

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
        metaswap_dll: str | Path,
        metaswap_dll_dependency: str | Path,
        modflow6_write_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """
        Write Ribasim, MetaSWAP and Modflow 6 model with exchange files, as well as a
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
        self.msw_model.write(directory / self._metaswap_model_dir)
        self.ribasim_model.write(directory / self._ribasim_model_dir)

        # Write exchange files
        exchange_dir = directory / "exchanges"
        exchange_dir.mkdir(mode=755, exist_ok=True)        
        coupling_dict = self.write_exchanges(directory)
        self.write_toml(
            directory, coupling_dict, modflow6_dll, ribasim_dll, ribasim_dll_dependency
        )

    def write_toml(
        self,
        directory: str | Path,
        coupling_dict: dict[str, Any],
        modflow6_dll: str | Path,
        metaswap_dll: str | Path,
        metaswap_dll_dependency: str | Path,
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
        metaswap_dll: str or Path
            Path to metaswap .dll. You can obtain this library by downloading
            `the last iMOD5 release
            <https://oss.deltares.nl/web/imod/download-imod5>`_
        metaswap_dll_dependency: str or Path
            Directory with metaswap .dll dependencies. Directory should contain:
            [fmpich2.dll, mpich2mpi.dll, mpich2nemesis.dll, TRANSOL.dll]. You
            can obtain these by downloading `the last iMOD5 release
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
                    "metaswap": {
                        "dll": str(metaswap_dll),
                        "dll_dep_dir": str(metaswap_dll_dependency),
                        "work_dir": self._metaswap_model_dir,
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
    def derive_river_drainage_coupling(
        gridded_basin: xr.DataArray,
        basin_ids: "pd.Series[int]",
        conductance: xr.DataArray,
    ) -> pd.DataFrame:
        # Conductance is leading parameter to define location, for both river
        # and drainage.
        # FUTURE: check for time dimension? Also order and inclusion of layer
        # in conductance.
        # Use xarray where to force the dimension order of conductance.
        basin_id = xr.where(conductance.notnull(), gridded_basin, np.nan)  # type: ignore
        include = basin_id.notnull().to_numpy()
        basin_id_values = basin_id.to_numpy()[include].astype(int)
        # Ribasim internally sorts the basin, which determines the order of the
        # Ribasim level array.
        basin_index = np.searchsorted(basin_ids, basin_id_values)
        boundary_index_values = np.cumsum(conductance.notnull().to_numpy().ravel()) - 1
        boundary_index_values = boundary_index_values[include.ravel()]
        return pd.DataFrame(
            data={"basin_index": basin_index, "bound_index": boundary_index_values}
        )

    def write_exchanges(
        self,
        directory: str | Path,
        mf6_rch_pkgkey: str,
        mf6_wel_pkgkey: str | None,
    ) -> dict[str, dict[str, str]]:
        gwf_names = self._get_gwf_modelnames()

        exchange_dir = Path(directory) / "exchanges"
        exchange_dir.mkdir(exist_ok=True, parents=True)

        # Assume only one groundwater flow model
        # FUTURE: Support multiple groundwater flow models.
        gwf_model = self.mf6_simulation[gwf_names[0]]
        coupling = self.coupling_list[0]
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
        gridded_basin = imod.prepare.rasterize(
            self.basin_definition,
            like=dis["idomain"].isel(layer=0, drop=True),
            column="node_id",
        )

        grid_data_key = [
            pkgname
            for pkgname, pkg in self.msw_model.items()
            if isinstance(pkg, GridData)
        ][0]
        index, svat = self.msw_model[grid_data_key].generate_index_array()
        grid_mapping = NodeSvatMapping(svat, dis)
        grid_mapping.write(directory, index, svat)

        recharge = gwf_model[mf6_rch_pkgkey]
        rch_mapping = RechargeSvatMapping(svat, recharge)
        rch_mapping.write(directory, index, svat)

        if self.is_sprinkling:
            well = gwf_model[mf6_wel_pkgkey]
            well_mapping = WellSvatMapping(svat, well)
            well_mapping.write(directory, index, svat)

        assert self.ribasim_model.basin.profile.df is not None
        basin_ids = np.unique(self.ribasim_model.basin.profile.df["node_id"])
        missing = ~np.isin(self.basin_definition["node_id"], basin_ids)
        if missing.any():
            missing_basins = self.basin_definition["node_id"].to_numpy()[missing]
            raise ValueError(
                "The node IDs of these basins in the basin definition do not "
                f"occur in the Ribasim model: {missing_basins}"
            )

        packages = asdict(coupling)
        coupling_dict: dict[str, Any] = {destination: {} for destination in packages}
        coupling_dict["mf6_model"] = packages.pop("mf6_model")
        for destination, keys in packages.items():
            for key in keys:
                package = gwf_model[key]
                table = self.derive_river_drainage_coupling(
                    gridded_basin, basin_ids, package["conductance"]
                )
                table.to_csv(exchange_dir / f"{key}.tsv", sep="\t", index=False)
                coupling_dict[destination][key] = f"exchanges/{key}.tsv"

        return coupling_dict
