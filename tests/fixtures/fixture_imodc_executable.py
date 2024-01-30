import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from imod_coupler.__main__ import run_coupler


@pytest.fixture(scope="session")
def imodc_executable(imod_coupler_exec_devel: Path) -> Callable[[Path], None]:
    """Replacement for subprocess.run"""
    if "pydevd" in sys.modules:

        def run_coupler_debug(file: Path) -> None:
            try:
                run_coupler(file)
            except Exception as ex:
                raise subprocess.CalledProcessError(1, "run_coupler", None, str(ex))

        return run_coupler_debug
    else:
        return lambda file: subprocess.run([imod_coupler_exec_devel, file], check=True)  # type: ignore # not interested in the return type of subprocess.run
