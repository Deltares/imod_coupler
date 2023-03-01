from pathlib import Path

from test_scripts.water_balance.combine import create_waterbalance_file
from test_utilities import compute_tolerance_oer_column_csvfiles


def test_waterbalance_script(
    tmp_path: Path, reference_result_folder: Path, test_data_folder: Path
):
    csv_result_file = tmp_path / "waterbalance_output.csv"

    create_waterbalance_file(
        test_data_folder / "tmodel_example_output" / "FlowFM_his.nc",
        test_data_folder / "tmodel_example_output" / "tot_svat_dtgw.csv",
        test_data_folder / "tmodel_example_output" / "T-MODEL-D.LST",
        output_file_csv=csv_result_file,
    )

    csv_reference_file = (
        reference_result_folder / "test_waterbalance_script" / "waterbalance_output.csv"
    )

    assert compute_tolerance_oer_column_csvfiles(
        csv_result_file, csv_reference_file, ";", abstol=0.001, reltol=0.001
    )
