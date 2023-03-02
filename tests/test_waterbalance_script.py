from pathlib import Path

from test_scripts.water_balance.combine import create_waterbalance_file
from test_utilities import numeric_csvfiles_equal


def test_waterbalance_script_case_1(
    tmp_path: Path, reference_result_folder: Path, test_data_folder: Path
):
    csv_result_file = tmp_path / "waterbalance_output.csv"

    create_waterbalance_file(
        test_data_folder / "tmodel_example_output" / "case_1" / "FlowFM_his.nc",
        test_data_folder / "tmodel_example_output" / "case_1" / "tot_svat_dtgw.csv",
        test_data_folder / "tmodel_example_output" / "case_1" / "T-MODEL-D.LST",
        output_file_csv=csv_result_file,
    )

    csv_reference_file = (
        reference_result_folder
        / "test_waterbalance_script"
        / "waterbalance_output_1.csv"
    )

    assert numeric_csvfiles_equal(
        csv_result_file, csv_reference_file, ";", abstol=0.001, reltol=0.001
    )


def test_waterbalance_script_case_2(
    tmp_path: Path, reference_result_folder: Path, test_data_folder: Path
):
    csv_result_file = tmp_path / "waterbalance_output.csv"

    create_waterbalance_file(
        test_data_folder / "tmodel_example_output" / "case_2" / "FlowFM_his.nc",
        test_data_folder / "tmodel_example_output" / "case_2" / "tot_svat_dtgw.csv",
        test_data_folder / "tmodel_example_output" / "case_2" / "T-MODEL-D.LST",
        output_file_csv=csv_result_file,
    )

    csv_reference_file = (
        reference_result_folder
        / "test_waterbalance_script"
        / "waterbalance_output_2.csv"
    )

    assert numeric_csvfiles_equal(
        csv_result_file, csv_reference_file, ";", abstol=0.001, reltol=0.001
    )
