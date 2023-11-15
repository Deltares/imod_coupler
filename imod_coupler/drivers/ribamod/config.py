import os
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, FilePath, validator

from imod_coupler.drivers.kernel_config import Modflow6, Ribasim


class Kernels(BaseModel):
    modflow6: Modflow6
    ribasim: Ribasim


class Coupling(BaseModel):
    mf6_model: str  # the MODFLOW 6 model that will be coupled
    mf6_active_river_packages: Dict[str, str]
    mf6_active_drainage_packages: Dict[str, str]
    mf6_passive_river_packages: Dict[str, str]
    mf6_passive_drainage_packages: Dict[str, str]
    output_config_file: FilePath | None = None

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
