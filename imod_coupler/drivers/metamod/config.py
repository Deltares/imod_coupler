import os
from pathlib import Path
from typing import Any, List

from pydantic import BaseModel, FilePath, validator

from imod_coupler.drivers.kernel_config import Metaswap, Modflow6


class Kernels(BaseModel):
    modflow6: Modflow6
    metaswap: Metaswap


class Coupling(BaseModel):
    enable_sprinkling: bool # true whemn sprinkling is active
    mf6_model: str  # the MODFLOW 6 model that will be coupled
    mf6_msw_recharge_pkg: str  # the recharge package that will be used for coupling
    mf6_msw_well_pkg: (
        str | None
    ) = None  # the well package that will be used for coupling when sprinkling is active
    mf6_msw_node_map: FilePath  # the path to the node map file
    mf6_msw_recharge_map: FilePath  # the path to the recharge map file
    mf6_msw_sprinkling_map: (
        FilePath | None
    ) = None  # the path to the sprinkling map file
    output_config_file: FilePath | None = None

    @validator("mf6_msw_well_pkg")
    def validate_mf6_msw_well_pkg(
        cls, mf6_msw_well_pkg: str | None, values: Any
    ) -> str | None:
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
        cls, mf6_msw_sprinkling_map: FilePath | None, values: Any
    ) -> FilePath | None:
        if mf6_msw_sprinkling_map is not None:
            return mf6_msw_sprinkling_map.resolve()
        elif values.get("enable_sprinkling"):
            raise ValueError(
                "If `enable_sprinkling` is True, then `mf6_msw_sprinkling_map` needs to be set."
            )
        return mf6_msw_sprinkling_map


class MetaModConfig(BaseModel):
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
