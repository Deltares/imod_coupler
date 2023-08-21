import os
from pathlib import Path
from typing import Any, List, Optional

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


class Kernels(BaseModel):
    modflow6: Modflow6
    ribasim: Ribasim


class Coupling(BaseModel):
    mf6_model: str  # the MODFLOW 6 model that will be coupled
    mf6_active_river_packages: List[str]
    mf6_active_drainage_packages: List[str]
    mf6_passive_river_packages: List[str]
    mf6_passive_drainage_packages: List[str]
    output_config_file: Optional[FilePath] = None

    @validator("output_config_file")
    def resolve_file_path(cls, file_path: FilePath) -> FilePath:
        return file_path.resolve()


class RibaModConfig(BaseModel):
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
