import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, FilePath, ValidationInfo, field_validator

from imod_coupler.drivers.kernel_config import Metaswap, Modflow6


class Kernels(BaseModel):
    modflow6: Modflow6
    metaswap: Metaswap


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
    mf6_node_max_layer: FilePath | None = None

    output_config_file: FilePath | None = None

    @field_validator("mf6_msw_node_map", "mf6_msw_recharge_map", "output_config_file")
    @classmethod
    def resolve_file_path(cls, file_path: FilePath) -> FilePath:
        return file_path.resolve()

    @field_validator("mf6_msw_sprinkling_map_groundwater")
    @classmethod
    def validate_mf6_msw_sprinkling_map(
        cls, mf6_msw_sprinkling_map_groundwater: FilePath | None, info: ValidationInfo
    ) -> FilePath | None:
        assert info.data is not None
        if mf6_msw_sprinkling_map_groundwater is not None:
            if info.data.get("mf6_msw_well_pkg") is None:
                raise ValueError(
                    "If 'mf6_msw_sprinkling_map_groundwater is set, then `mf6_msw_well_pkg` needs to be set."
                )
            return mf6_msw_sprinkling_map_groundwater.resolve()
        return mf6_msw_sprinkling_map_groundwater

    @field_validator("mf6_msw_sprinkling_map")
    @classmethod
    def validate_sprinkling_map_label(
        cls, mf6_msw_sprinkling_map: FilePath | None
    ) -> None:
        if mf6_msw_sprinkling_map is not None:
            raise ValueError(
                "The use of 'mf6_msw_sprinkling_map' label is depricated; now use mf6_msw_sprinkling_map_groundwater"
            )


class MetaModConfig(BaseModel):
    kernels: Kernels
    coupling: list[Coupling]

    def __init__(self, config_dir: Path, **data: Any) -> None:
        """Model for the MetaMod config validated by pydantic

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
