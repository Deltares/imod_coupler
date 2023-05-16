from pathlib import Path
from typing import Dict, Tuple

from test_scripts.mf6_water_balance.combine import create_modflow_waterbalance_file
from test_utilities import numeric_csvfiles_equal

eps = 1e-4
tolerance_balance: Dict[str, Tuple[float, float]] = {
    "default": (2 * eps, 2 * eps),
}


def test_waterbalance_script_case_1(
    tmp_path: Path, reference_result_folder: Path, test_data_folder: Path
):
    script_test_data_folder = test_data_folder / "waterbalance_script"
    csv_result_file = tmp_path / "waterbalance_output.csv"

    create_modflow_waterbalance_file(
        script_test_data_folder / "T-MODEL-D.LST",
        output_file_csv=csv_result_file,
    )

    csv_reference_file = (
        reference_result_folder
        / "test_waterbalance_script"
        / "waterbalance_output_1.csv"
    )

    assert numeric_csvfiles_equal(
        csv_result_file, csv_reference_file, ";", tolerance_balance
    )
