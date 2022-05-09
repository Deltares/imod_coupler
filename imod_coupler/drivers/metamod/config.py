from typing import Any, Optional

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


class Kernels(BaseModel):
    modflow6: Kernel
    metaswap: Kernel


class Coupling(BaseModel):
    enable_sprinkling: bool
    mf6_model: str
    mf6_msw_recharge_pkg: str
    mf6_msw_well_pkg: Optional[str]
    mf6_msw_node_map: FilePath
    mf6_msw_recharge_map: FilePath
    mf6_msw_sprinkling_map = Optional[FilePath]

    @validator("mf6_msw_well_pkg")
    def validate_mf6_msw_well_pkg(
        cls, mf6_msw_well_pkg: Optional[str], values: Any
    ) -> Optional[str]:
        if values.get("enable_sprinkling") and mf6_msw_well_pkg is None:
            raise ValueError(
                "If `enable_sprinkling` is True, then `mf6_msw_well_pkg` needs to be set."
            )
        return mf6_msw_well_pkg

    @validator("mf6_msw_node_map")
    def resolve_mf6_msw_node_map(cls, mf6_msw_node_map: FilePath) -> FilePath:
        return mf6_msw_node_map.resolve()

    @validator("mf6_msw_recharge_map")
    def resolve_mf6_msw_recharge_map(cls, mf6_msw_recharge_map: FilePath) -> FilePath:
        return mf6_msw_recharge_map.resolve()

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


class Config(BaseModel):
    kernels: Kernels
    coupling: Coupling
