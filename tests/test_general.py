import subprocess
from pathlib import Path

from imod_coupler import __version__


def test_get_version(imodc_path: Path) -> None:
    output_version = subprocess.run(
        [imodc_path, "--version"], capture_output=True, text=True
    ).stdout.strip("\n")

    expected_version = f"{imodc_path.name} {__version__}"

    assert output_version == expected_version
