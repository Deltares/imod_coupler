import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, FilePath, ValidationInfo, field_validator

from imod_coupler.drivers.kernel_config import Megaswap, Modflow6


class Kernels(BaseModel):
    modflow6: Modflow6
    megaswap: Megaswap


class Coupling(BaseModel):
    mf6_model: str  # the MODFLOW 6 model that will be coupled
    mf6_msw_recharge_pkg: str  # the recharge package that will be used for coupling
    mf6_msw_well_pkg: str | None = (
        None  # the well package that will be used for coupling when sprinkling is active
    )
    mf6_msw_node_map: FilePath  # the path to the node map file
    mf6_msw_recharge_map: FilePath  # the path to the recharge map file
    mf6_msw_sprinkling_map_groundwater: FilePath | None = (
        None  # the path to the sprinkling map file
    )
    # for deprecation warning on label
    mf6_msw_sprinkling_map: FilePath | None = None

    output_config_file: FilePath | None = None

    @field_validator("mf6_msw_node_map", "mf6_msw_recharge_map", "output_config_file")
    @classmethod
    def resolve_file_path(cls, file_path: FilePath) -> FilePath:
        return file_path.resolve()


class MegaModConfig(BaseModel):
    kernels: Kernels
    coupling: list[Coupling]

    def __init__(self, config_dir: Path, **data: Any) -> None:
        """Model for the MegaMod config validated by pydantic

        The validation expects current working directory at config file level
        so it is changed during initialization

        Args:
            config_dir (Path): Directory where the config file resides
        """
        os.chdir(config_dir)
        super().__init__(**data)

    @field_validator("coupling")
    @classmethod
    def restrict_coupling_count(cls, coupling: list[Coupling]) -> list[Coupling]:
        if len(coupling) == 0:
            raise ValueError("At least one coupling has to be defined.")
        if len(coupling) > 1:
            raise ValueError("Multi-model coupling is not yet supported.")
        return coupling
