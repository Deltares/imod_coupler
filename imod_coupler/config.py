from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, validator


class Log(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DriverType(str, Enum):
    METAMOD = "metamod"


class BaseConfig(BaseModel):
    config_file: Path
    log_level: Log = Log.INFO
    log_file: Path
    timing: bool = False
    driver_type: DriverType
    driver: Any = ...

    @validator("log_file")
    def resolve_log_file(cls, log_file: Any) -> Any:
        return log_file.resolve()
