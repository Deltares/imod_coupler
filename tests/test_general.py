import subprocess
from pathlib import Path

from loguru import logger

from imod_coupler import __version__
from imod_coupler.config import LogLevel
from imod_coupler.utils import setup_logger


def test_get_version(imod_coupler_exec_devel: Path) -> None:
    output_version = subprocess.run(
        [imod_coupler_exec_devel, "--version"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip("\n")

    assert output_version == __version__


def test_log_file(
    tmp_path: Path,
) -> None:
    """Assures that logs are written to file after `setup_logger` is called"""

    test_string = "Test"
    log_file = tmp_path / "imod_coupler.log"
    setup_logger(LogLevel.INFO, log_file)
    logger.warning(test_string)

    with open(log_file) as f:
        assert test_string in f.read()
