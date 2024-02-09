from pydantic import BaseModel, DirectoryPath, FilePath, field_validator


class Modflow6(BaseModel):
    dll: FilePath
    dll_dep_dir: DirectoryPath | None = None
    work_dir: DirectoryPath

    @field_validator("dll")
    @classmethod
    def resolve_dll(cls, dll: FilePath) -> FilePath:
        return dll.resolve()

    @field_validator("dll_dep_dir")
    @classmethod
    def resolve_dll_dep_dir(
        cls, dll_dep_dir: DirectoryPath | None
    ) -> DirectoryPath | None:
        if dll_dep_dir is not None:
            dll_dep_dir = dll_dep_dir.resolve()
        return dll_dep_dir


class Metaswap(BaseModel):
    dll: FilePath
    dll_dep_dir: DirectoryPath
    work_dir: DirectoryPath

    @field_validator("dll")
    @classmethod
    def resolve_dll(cls, dll: FilePath) -> FilePath:
        return dll.resolve()

    @field_validator("dll_dep_dir")
    @classmethod
    def resolve_dll_dep_dir(
        cls, dll_dep_dir: DirectoryPath | None
    ) -> DirectoryPath | None:
        if dll_dep_dir is not None:
            dll_dep_dir = dll_dep_dir.resolve()
        return dll_dep_dir


class Ribasim(BaseModel):
    dll: FilePath
    dll_dep_dir: DirectoryPath
    config_file: FilePath

    @field_validator("dll")
    @classmethod
    def resolve_dll(cls, dll: FilePath) -> FilePath:
        return dll.resolve()

    @field_validator("dll_dep_dir")
    @classmethod
    def resolve_dll_dep_dir(
        cls, dll_dep_dir: DirectoryPath | None
    ) -> DirectoryPath | None:
        if dll_dep_dir is not None:
            dll_dep_dir = dll_dep_dir.resolve()
        return dll_dep_dir
