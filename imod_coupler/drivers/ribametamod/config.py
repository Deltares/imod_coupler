import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, FilePath, ValidationInfo, field_validator

from imod_coupler.drivers.kernel_config import Metaswap, Modflow6, Ribasim


class Kernels(BaseModel):
    modflow6: Modflow6
    ribasim: Ribasim | None
    metaswap: Metaswap | None


class Coupling(BaseModel):
    mf6_model: str  # the MODFLOW 6 model that will be coupled
    mf6_active_river_packages: dict[str, str]
    mf6_active_drainage_packages: dict[str, str]
    mf6_passive_river_packages: dict[str, str]
    mf6_passive_drainage_packages: dict[str, str]

    enable_sprinkling_groundwater: bool = False  # true when sprinkling is active
    mf6_msw_recharge_pkg: str = (
        ""  # the recharge package that will be used for coupling
    )
    mf6_msw_well_pkg: str | None = (
        None  # the well package that will be used for coupling when sprinkling is active
    )
    mf6_msw_node_map: FilePath | None = None  # the path to the node map file
    mf6_msw_recharge_map: FilePath | None = None  # the pach to the recharge map file
    mf6_msw_sprinkling_map_groundwater: FilePath | None = (
        None  # the path to the sprinkling map file (optional)
    )
    mf6_msw_ponding_map_groundwater: FilePath | None = (
        None  # the path to the ponding map file (optional)
    )
    output_config_file: FilePath | None = None

    enable_sprinkling_surface_water: bool = False  # true when sprinkling is active
    rib_msw_sprinkling_map_surface_water: FilePath | None = (
        None  # the path to the sprinkling map file
    )
    rib_msw_ponding_map_surface_water: FilePath | None = (
        None  # the path to the ponding map file
    )

    @field_validator("mf6_msw_well_pkg")
    @classmethod
    def validate_mf6_msw_well_pkg(
        cls, mf6_msw_well_pkg: str | None, info: ValidationInfo
    ) -> str | None:
        assert info.config is not None
        if (
            info.config.get("enable_sprinkling_groundwater")
            and mf6_msw_well_pkg is None
        ):
            raise ValueError(
                "If `enable_sprinkling_groundwater` is True, then `mf6_msw_well_pkg` needs to be set."
            )
        return mf6_msw_well_pkg

    @field_validator(
        "output_config_file",
        "mf6_msw_node_map",
        "mf6_msw_recharge_map",
        "output_config_file",
    )
    @classmethod
    def resolve_file_path(cls, file_path: FilePath) -> FilePath:
        return file_path.resolve()

    @field_validator("mf6_msw_sprinkling_map_groundwater")
    @classmethod
    def validate_mf6_msw_sprinkling_map(
        cls, mf6_msw_sprinkling_map_groundwater: FilePath | None, info: ValidationInfo
    ) -> FilePath | None:
        assert info.config is not None
        if mf6_msw_sprinkling_map_groundwater is not None:
            return mf6_msw_sprinkling_map_groundwater.resolve()
        elif info.config.get("enable_sprinkling_groundwater"):
            raise ValueError(
                "If `enable_sprinkling_groundwater` is True, then `mf6_msw_sprinkling_map_groundwater` needs to be set."
            )
        return mf6_msw_sprinkling_map_groundwater


class RibaMetaModConfig(BaseModel):
    kernels: Kernels
    coupling: list[Coupling]

    def __init__(self, config_dir: Path, **data: Any) -> None:
        """Model for the Ribamod config validated by pydantic

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
