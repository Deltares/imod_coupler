from pathlib import Path


def test_lookup_table_present(database_path: Path) -> None:
    assert database_path.is_dir()
