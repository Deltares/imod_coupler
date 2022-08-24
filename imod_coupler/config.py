import os
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, FilePath, validator


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class DriverType(str, Enum):
    METAMOD = "metamod"


class BaseConfig(BaseModel):
    """Model for the base config validated by pydantic"""

    log_level: LogLevel = LogLevel.INFO
    timing: bool = False
    driver_type: DriverType
    driver: BaseModel
