import subprocess
from pathlib import Path

from imod_coupler import __version__


def test_get_version(imodc: Path) -> None:
    output_version = subprocess.run(
        [imodc, "--version"], capture_output=True, text=True
    ).stdout.strip("\n")

    assert output_version == __version__
