import pytest

import imod_coupler.parser
from imod_coupler import __version__


def test_get_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as cm:
        imod_coupler.parser.parse_args(["--version"])
    assert cm.value.code == 0
    captured = capsys.readouterr()
    output_version = captured.out.strip()
    assert output_version is not None
    assert output_version == __version__
