import subprocess
from pathlib import Path

from imod_coupler import __version__


def test_get_version(imod_coupler_exec_devel: Path) -> None:
    output_version = subprocess.run(
        [imod_coupler_exec_devel, "--version"], capture_output=True, text=True, check=True
    ).stdout.strip("\n")

    assert output_version == __version__
