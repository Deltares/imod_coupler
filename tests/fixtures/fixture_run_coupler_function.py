import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import concurrent
import pytest

from imod_coupler.__main__ import run_coupler


def _run_coupler_worker(file: Path) -> None:
    run_coupler(file)


@pytest.fixture(scope="session")
def run_coupler_function(imod_coupler_exec_devel: Path) -> Callable[[Path], None]:
    """
    Replacement for subprocess.run.
    If pydevd is loaded, don't use subprocess.run but call run_coupler directly.
    Otherwise it would not be possible to attach the debugger.
    pydevd is loaded when starting the debugger via Visual Studio Code (PyCharm is untested).
    """
    if "pydevd" in sys.modules or imod_coupler_exec_devel == Path("local"):

        def run_coupler_debug(file: Path) -> None:
            # Start the coupler in a separate process. This avoids dll unloading issues
            # when the dll crashes.
            executor = concurrent.futures.ProcessPoolExecutor(max_workers=1)
            try:
                future = executor.submit(_run_coupler_worker, file)
                future.result()
            except Exception as e:
                raise subprocess.CalledProcessError(returncode=1, cmd=[str(run_coupler), str(file)], output=None, stderr=e.args[0])
            finally:
                executor.shutdown(wait=False)


        return run_coupler_debug
    else:
        return lambda file: subprocess.run([imod_coupler_exec_devel, file], check=True)  # type: ignore # not interested in the return type of subprocess.run
