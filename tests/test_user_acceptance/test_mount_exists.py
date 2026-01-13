"""
Tests to verify that the mount point for the user acceptance metaswap database exists.
"""

import pytest
from pathlib import Path


@pytest.mark.user_acceptance
def test_mount_exists(user_acceptance_metaswap_dbase: Path) -> None:
    assert user_acceptance_metaswap_dbase.exists()
