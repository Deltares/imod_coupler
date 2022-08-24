import sys
from pathlib import Path

from loguru import logger
from pytest import CaptureFixture

from imod_coupler.config import LogLevel
from imod_coupler.utils import setup_logger


def test_log_file(
    tmp_path: Path,
) -> None:
    """Assures that logs are written to file after `setup_logger` is called"""

    test_string = "Test"
    log_file = tmp_path / "imod_coupler.log"
    setup_logger(LogLevel.INFO, log_file)
    logger.warning(test_string)

    with open(log_file, "r") as f:
        assert test_string in f.read()
