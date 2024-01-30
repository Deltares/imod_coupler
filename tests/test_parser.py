import pytest

import imod_coupler.parser
from imod_coupler import __version__


def test_get_version() -> None:
    with pytest.raises(SystemExit) as cm:
        output_version = imod_coupler.parser.parse_args(["--version"])
        assert cm.value.code == 0
        assert output_version is not None
        assert output_version == __version__
