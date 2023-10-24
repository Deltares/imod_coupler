from pathlib import Path
from typing import Optional, Union

import tomli_w
from hydrolib.core.dflowfm.mdu.models import FMModel
from imod.couplers.metamod.node_svat_mapping import NodeSvatMapping
from imod.couplers.metamod.rch_svat_mapping import RechargeSvatMapping
from imod.couplers.metamod.wel_svat_mapping import WellSvatMapping
from imod.mf6 import Modflow6Simulation
from imod.msw import GridData, MetaSwapModel, Sprinkling


class DfmMetaModModel:
    """
    The Dfm_MetaMod class creates the necessary input files for coupling MetaSWAP,
    MODFLOW 6 and Dflow-FM.

    Parameters
    ----------
    msw_model : MetaSwapModel
        The MetaSWAP model that should be coupled.
    mf6_simulation : Modflow6Simulation
        The Modflow6 simulation that should be coupled.
    dfm_model:
        DFlow-FM model that should be coupled
    mf6_rch_pkgkey: str
        Key of Modflow 6 recharge package to which MetaSWAP is coupled.
    mf6_wel_correction_pkgkey: str
        key of Modflow 6 well package used for applying the correction flux
    mf6_wel_pkgkey: str or None
        Optional key of Modflow 6 well package to which MetaSWAP sprinkling is
        coupled.
    """

    _toml_name = "imod_coupler.toml"
    _modflow6_model_dir = "Modflow6"
    _metaswap_model_dir = "MetaSWAP"
    _dfm_model_dir = "dflow-fm"

    def __init__(
        self,
        msw_model: MetaSwapModel,
        mf6_simulation: Modflow6Simulation,
        dfm_model: FMModel,
        mf6_rch_pkgkey: str,
        mf6_river_active_pkgkey: str,
        mf6_river_passive_pkgkey: str,
        mf6_wel_correction_pkgkey: str,
        mf6_wel_pkgkey: str,
        mf6_river_to_dfm_1d_q_dmm_path: Path,
        dfm_1d_waterlevel_to_mf6_river_stage_dmm_path: Path,
        mf6_river2_to_dfm_1d_q_dmm_path: Path,
        mf6_drainage_to_dfm_1d_q_dmm_path: Path,
        msw_runoff_to_dfm_1d_q_dmm_path: Path,
        msw_sprinkling_to_dfm_1d_q_dmm_path: Path,
        msw_ponding_to_dfm_2d_dv_dmm_path: Path,
        dfm_2d_waterlevels_to_msw_h_dmm_path: Path,
        dfm_1d_points_dat_path: Path,
        output_config_file: Path,
    ):
        self.msw_model = msw_model
        self.mf6_simulation = mf6_simulation
        self.mf6_rch_pkgkey = mf6_rch_pkgkey
        self.mf6_wel_pkgkey = mf6_wel_pkgkey
        self.mf6_wel_correction_pkgkey = mf6_wel_correction_pkgkey
        self.mf6_river_active_pkgkey = mf6_river_active_pkgkey
        self.mf6_river_passive_pkgkey = mf6_river_passive_pkgkey
        self.dfm_model = dfm_model
        self.is_sprinkling = self._check_coupler_and_sprinkling()
        self.output_config_file = output_config_file
        self.mapping_files = {}
        self.mapping_files["mf6_river_to_dfm_1d_q_dmm"] = mf6_river_to_dfm_1d_q_dmm_path
        self.mapping_files[
            "dfm_1d_waterlevel_to_mf6_river_stage_dmm"
        ] = dfm_1d_waterlevel_to_mf6_river_stage_dmm_path
        self.mapping_files[
            "mf6_river2_to_dfm_1d_q_dmm"
        ] = mf6_river2_to_dfm_1d_q_dmm_path
        self.mapping_files[
            "mf6_drainage_to_dfm_1d_q_dmm"
        ] = mf6_drainage_to_dfm_1d_q_dmm_path
        self.mapping_files[
            "msw_runoff_to_dfm_1d_q_dmm"
        ] = msw_runoff_to_dfm_1d_q_dmm_path

        self.mapping_files[
            "msw_sprinkling_to_dfm_1d_q_dmm"
        ] = msw_sprinkling_to_dfm_1d_q_dmm_path

        self.mapping_files[
            "msw_ponding_to_dfm_2d_dv_dmm"
        ] = msw_ponding_to_dfm_2d_dv_dmm_path
        self.mapping_files[
            "dfm_2d_waterlevels_to_msw_h_dmm"
        ] = dfm_2d_waterlevels_to_msw_h_dmm_path
        self.mapping_files["dfm_1d_points_dat"] = dfm_1d_points_dat_path

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

    def write(
        self,
        directory: Union[str, Path],
        modflow6_dll: Union[str, Path],
        metaswap_dll: Union[str, Path],
        metaswap_dll_dependency: Union[str, Path],
        dflowfm_dll: Union[str, Path],
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
        dflowfm_dll: str or Path
            Directory with dflowfm.dll as well as all of its dependencies.
        """
        # force to Path
        directory = Path(directory)
        # For some reason the Modflow 6 model has to be written before
        # writing the MetaSWAP model. Else we get an Access Violation Error when
        # running the coupler.
        self.dfm_model.save(directory / self._dfm_model_dir / "dfm.mdu", recurse=True)
        self.mf6_simulation.write(directory / self._modflow6_model_dir)
        self.msw_model.write(directory / self._metaswap_model_dir)

        # Write exchange files
        exchange_dir = directory / "exchanges"
        exchange_dir.mkdir(mode=755, exist_ok=True)
        self.write_exchanges(exchange_dir, self.mf6_rch_pkgkey, self.mf6_wel_pkgkey)

        coupling_dict = self._get_coupling_dict(
            exchange_dir,
            self.mf6_rch_pkgkey,
            self.mf6_river_active_pkgkey,
            self.mf6_river_passive_pkgkey,
            self.mf6_wel_correction_pkgkey,
            self.mf6_wel_pkgkey,
            self.output_config_file,
        )

        self.write_toml(
            directory,
            modflow6_dll,
            metaswap_dll,
            metaswap_dll_dependency,
            dflowfm_dll,
            coupling_dict,
        )

    def write_toml(
        self,
        directory: Union[str, Path],
        modflow6_dll: Union[str, Path],
        metaswap_dll: Union[str, Path],
        metaswap_dll_dependency: Union[str, Path],
        dflowfm_dll: Union[str, Path],
        coupling_dict: dict[str, Union[bool, str]],
    ) -> None:
        # force to Path
        directory = Path(directory)

        toml_path = directory / self._toml_name

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

        toml_path = directory / self._toml_name

        coupler_toml = {
            "timing": False,
            "log_level": "INFO",
            "driver_type": "dfm_metamod",
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
                    "dflowfm": {
                        "dll": str(dflowfm_dll),
                        "work_dir": f".\\{self._dfm_model_dir}",
                    },
                },
                "coupling": [coupling_dict],
            },
        }

        with open(toml_path, "wb") as f:
            tomli_w.dump(coupler_toml, f)

    def _get_gwf_modelnames(self) -> list[str]:
        """
        Get names of gwf models in mf6 simulation
        """
        return [
            key
            for key, value in self.mf6_simulation.items()
            if type(value).__name__ == "GroundwaterFlowModel"
        ]

    def _get_dfm_modelname(self) -> str:
        return "dfm.mdu"

    def _get_coupling_dict(
        self,
        directory: Path,
        mf6_rch_pkgkey: str,
        mf6_active_riv_pkgkey: str,
        mf6_passive_riv_pkgkey: str,
        mf6_wel_correction_pkgkey: str,
        mf6_wel_pkgkey: Optional[str],
        output_config_file: Optional[Path],
    ) -> dict[str, Union[bool, str]]:
        """
        Get dictionary with names of coupler packages and paths to mappings.

        Parameters
        ----------
        directory: str or Path
            Directory where .dxc files are written.
        mf6_rch_pkgkey: str
            Key of Modflow 6 recharge package to which MetaSWAP is coupled.
        mf6_wel_correction_pkgkey: str
            key of Modflow 6 well package used for applying the correction flux
        mf6_wel_pkgkey: str
            Key of Modflow 6 well package to which MetaSWAP sprinkling is
            coupled.
        mf6_riv_pkgkey: str
             Key of Modflow 6  river package
        Returns
        -------
        coupling_dict: dict
            Dictionary with names of coupler packages and paths to mappings.
        """

        coupling_dict = dict[str, Union[bool, str]]()

        gwf_names = self._get_gwf_modelnames()

        coupling_dict["dfm_model"] = self._get_dfm_modelname()

        # Assume only one groundwater flow model
        # FUTURE: Support multiple groundwater flow models.
        coupling_dict["mf6_model"] = gwf_names[0]

        coupling_dict[
            "mf6_msw_node_map"
        ] = f"./{directory.name}/{NodeSvatMapping._file_name}"

        coupling_dict["mf6_msw_recharge_pkg"] = mf6_rch_pkgkey
        coupling_dict["mf6_river_active_pkg"] = mf6_active_riv_pkgkey
        coupling_dict["mf6_river_passive_pkg"] = mf6_passive_riv_pkgkey
        coupling_dict["mf6_wel_correction_pkgkey"] = mf6_wel_correction_pkgkey
        coupling_dict[
            "mf6_msw_recharge_map"
        ] = f"./{directory.name}/{RechargeSvatMapping._file_name}"

        if self.is_sprinkling:
            if mf6_wel_pkgkey is None:
                raise ValueError("mf6_wel_pkgkey is required when using sprikling")
            coupling_dict["mf6_msw_well_pkg"] = mf6_wel_pkgkey
            coupling_dict[
                "mf6_msw_sprinkling_map"
            ] = f"./{directory.name}/{WellSvatMapping._file_name}"

        for mapping_name, mapping_path in self.mapping_files.items():
            if mapping_path:
                coupling_dict[mapping_name] = str(mapping_path)
        coupling_dict["output_config_file"] = str(output_config_file)
        return coupling_dict

    def write_exchanges(
        self,
        directory: Union[str, Path],
        mf6_rch_pkgkey: str,
        mf6_wel_pkgkey: Optional[str],
    ) -> None:
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

        gwf_names = self._get_gwf_modelnames()

        # Assume only one groundwater flow model
        # FUTURE: Support multiple groundwater flow models.
        gwf_model = self.mf6_simulation[gwf_names[0]]

        grid_data_key = [
            pkgname
            for pkgname, pkg in self.msw_model.items()
            if isinstance(pkg, GridData)
        ][0]

        dis = gwf_model[gwf_model._get_pkgkey("dis")]

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
