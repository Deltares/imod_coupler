import os
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, FilePath, validator


class Log(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DriverType(str, Enum):
    METAMOD = "metamod"


class BaseConfig(BaseModel):
    log_level: Log = Log.INFO
    log_file: Path
    timing: bool = False
    driver_type: DriverType
    driver: BaseModel

    def __init__(self, config_dir: Path, **data: Any) -> None:
        # Validation expects current working directory at config file level
        os.chdir(config_dir)
        super().__init__(**data)

    @validator("log_file")
    def resolve_log_file(cls, log_file: Path) -> Path:
        return log_file.resolve()
