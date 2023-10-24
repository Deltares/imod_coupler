import os
from pathlib import Path
from typing import Any, List, Optional

from pydantic import BaseModel, DirectoryPath, FilePath, validator


class Kernel(BaseModel):
    dll: FilePath
    dll_dep_dir: Optional[DirectoryPath]
    work_dir: DirectoryPath

    @validator("dll")
    def resolve_dll(cls, dll: FilePath) -> FilePath:
        return dll.resolve()

    @validator("dll_dep_dir")
    def resolve_dll_dep_dir(
        cls, dll_dep_dir: Optional[DirectoryPath]
    ) -> Optional[DirectoryPath]:
        if dll_dep_dir is not None:
            dll_dep_dir = dll_dep_dir.resolve()
        return dll_dep_dir

    @validator("work_dir")
    def resolve_work_dir(cls, work_dir: FilePath) -> FilePath:
        return work_dir.resolve()


class Kernels(BaseModel):
    dflowfm: Kernel
    modflow6: Kernel
    metaswap: Kernel


class Coupling(BaseModel):
    mf6_model: str  # the MODFLOW 6 model that will be coupled
    dfm_model: str  # the dflow-fm model that will be coupled
    mf6_msw_recharge_pkg: str  # the recharge package that will be used for coupling
    mf6_wel_correction_pkg: str  # key of Modflow 6 well package used for applying the correction flux
    mf6_msw_well_pkg: Optional[
        str
    ] = None  # the well package that will be used for coupling when sprinkling is active
    mf6_river_active_pkg: str  # the river package that will be used for active coupling with dflow
    mf6_river_passive_pkg: str  # the river package that will be used for apassive coupling with dflow
    mf6_drain_pkg: str  # the river package that will be used for passive coupling with dflow
    mf6_msw_node_map: FilePath  # the path to the node map file
    mf6_msw_recharge_map: FilePath  # the pach to the recharge map file

    mf6_river_to_dfm_1d_q_dmm: Optional[FilePath]
    dfm_1d_waterlevel_to_mf6_river_stage_dmm: Optional[FilePath]
    mf6_river2_to_dfm_1d_q_dmm: Optional[FilePath]
    mf6_drainage_to_dfm_1d_q_dmm: Optional[FilePath]
    msw_runoff_to_dfm_1d_q_dmm: Optional[FilePath]

    msw_sprinkling_to_dfm_1d_q_dmm: Optional[FilePath]

    dfm_2d_waterlevels_to_msw_h_dmm: Optional[FilePath]
    msw_ponding_to_dfm_2d_dv_dmm: Optional[FilePath]
    mf6_msw_sprinkling_map: Optional[
        FilePath
    ] = None  # the path to the sprinkling map file
    output_config_file: FilePath

    class Config:
        arbitrary_types_allowed = True  # Needed for `mf6_msw_sprinkling_map`

    @validator("mf6_wel_correction_pkg")
    def validate_mf6_wel_correction_pkg(
        cls, mf6_wel_correction_pkg: str, values: Any
    ) -> str:
        if mf6_wel_correction_pkg == "":
            raise ValueError(
                "Name of the correction flux well package cannot be empty."
            )
        return mf6_wel_correction_pkg

    @validator("mf6_msw_node_map")
    def resolve_mf6_msw_node_map(cls, mf6_msw_node_map: FilePath) -> FilePath:
        return mf6_msw_node_map.resolve()

    @validator(
        "mf6_river_to_dfm_1d_q_dmm",
        "dfm_1d_waterlevel_to_mf6_river_stage_dmm",
        "mf6_river2_to_dfm_1d_q_dmm",
        "mf6_drainage_to_dfm_1d_q_dmm",
        "msw_runoff_to_dfm_1d_q_dmm",
        "dfm_2d_waterlevels_to_msw_h_dmm",
        "msw_sprinkling_to_dfm_1d_q_dmm",
        "msw_ponding_to_dfm_2d_dv_dmm",
        "dfm_2d_waterlevels_to_msw_h_dmm",
        "msw_ponding_to_dfm_2d_dv_dmm",
    )
    def resolve_mapping_files(cls, mapping_file: FilePath) -> FilePath:
        return mapping_file.resolve()

    @validator("mf6_msw_recharge_map")
    def resolve_mf6_msw_recharge_map(cls, mf6_msw_recharge_map: FilePath) -> FilePath:
        return mf6_msw_recharge_map.resolve()

    @validator("mf6_msw_sprinkling_map")
    def validate_mf6_msw_sprinkling_map(
        cls, mf6_msw_sprinkling_map: Optional[FilePath], values: Any
    ) -> Optional[FilePath]:
        if mf6_msw_sprinkling_map:
            return mf6_msw_sprinkling_map.resolve()
        return mf6_msw_sprinkling_map

    @validator("dfm_model")
    def validate_dfm_model_is_mdu(cls, dfm_model: str) -> str:
        if dfm_model[-3:].lower() != "mdu":
            raise ValueError("the dflow fm model name should end in mdu")
        return dfm_model

    @validator("output_config_file")
    def validate_toml_file(cls, filename: FilePath) -> FilePath:
        if os.path.splitext(filename.name)[1].lower() != ".toml":
            raise ValueError("expected a toml file")
        return filename.resolve()

    def validate_sprinkling_settings(self) -> None:
        sprinkling_settings_present = [
            self.mf6_msw_well_pkg is not None,
            self.mf6_msw_sprinkling_map is not None,
        ]
        if all(setting is True for setting in sprinkling_settings_present) or all(
            setting is False for setting in sprinkling_settings_present
        ):
            return
        raise ValueError(
            "mf6_msw_sprinkling_map and mf6_msw_well_pkg must both be present or both be absent "
        )

    def enable_sprinkling(self) -> bool:
        return (
            self.mf6_msw_well_pkg is not None
            and self.mf6_msw_sprinkling_map is not None
        )


class DfmMetaModConfig(BaseModel):
    kernels: Kernels
    coupling: List[Coupling]

    def __init__(self, config_dir: Path, **data: Any) -> None:
        """Model for the MetaMod config validated by pydantic

        The validation expects current working directory at config file level
        so it is changed during initialization

        Args:
            config_dir (Path): Directory where the config file resides
        """
        os.chdir(config_dir)
        super().__init__(**data)

    @validator("coupling")
    def restrict_coupling_count(cls, coupling: List[Coupling]) -> List[Coupling]:
        if len(coupling) == 0:
            raise ValueError("At least one coupling has to be defined.")
        if len(coupling) > 1:
            raise ValueError("Multi-model coupling is not yet supported.")
        return coupling
