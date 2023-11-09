import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, DirectoryPath, FilePath, validator


class Modflow6(BaseModel):
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


class Ribasim(BaseModel):
    dll: FilePath
    dll_dep_dir: DirectoryPath
    config_file: FilePath

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


class Metaswap(BaseModel):
    dll: FilePath
    dll_dep_dir: DirectoryPath
    config_file: FilePath

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


class Kernels(BaseModel):
    modflow6: Modflow6
    ribasim: Ribasim
    metaswap: Metaswap


class Coupling(BaseModel):
    mf6_model: str  # the MODFLOW 6 model that will be coupled
    mf6_active_river_packages: Dict[str, str]
    mf6_active_drainage_packages: Dict[str, str]
    mf6_passive_river_packages: Dict[str, str]
    mf6_passive_drainage_packages: Dict[str, str]
    output_config_file: Optional[FilePath] = None
    
    enable_sprinkling: bool  # true whemn sprinkling is active
    mf6_msw_recharge_pkg: str  # the recharge package that will be used for coupling
    mf6_msw_well_pkg: Optional[
        str
    ] = None  # the well package that will be used for coupling when sprinkling is active
    mf6_msw_node_map: FilePath  # the path to the node map file
    mf6_msw_recharge_map: FilePath  # the pach to the recharge map file
    mf6_msw_sprinkling_map: Optional[
        FilePath
    ] = None  # the path to the sprinkling map file
    output_config_file: Optional[FilePath] = None

    class Config:
        arbitrary_types_allowed = True  # Needed for `mf6_msw_sprinkling_map`
    
    @validator("output_config_file")
    def resolve_file_path(cls, file_path: FilePath) -> FilePath:
        return file_path.resolve()

    @validator("mf6_msw_well_pkg")
    def validate_mf6_msw_well_pkg(
        cls, mf6_msw_well_pkg: Optional[str], values: Any
    ) -> Optional[str]:
        if values.get("enable_sprinkling") and mf6_msw_well_pkg is None:
            raise ValueError(
                "If `enable_sprinkling` is True, then `mf6_msw_well_pkg` needs to be set."
            )
        return mf6_msw_well_pkg

    @validator("mf6_msw_node_map", "mf6_msw_recharge_map", "output_config_file")
    def resolve_file_path(cls, file_path: FilePath) -> FilePath:
        return file_path.resolve()

    @validator("mf6_msw_sprinkling_map")
    def validate_mf6_msw_sprinkling_map(
        cls, mf6_msw_sprinkling_map: Optional[FilePath], values: Any
    ) -> Optional[FilePath]:
        if mf6_msw_sprinkling_map is not None:
            return mf6_msw_sprinkling_map.resolve()
        elif values.get("enable_sprinkling"):
            raise ValueError(
                "If `enable_sprinkling` is True, then `mf6_msw_sprinkling_map` needs to be set."
            )
        return mf6_msw_sprinkling_map


class RibaMetaModConfig(BaseModel):
    kernels: Kernels
    coupling: List[Coupling]

    def __init__(self, config_dir: Path, **data: Any) -> None:
        """Model for the Ribamod config validated by pydantic

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
