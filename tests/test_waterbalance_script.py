# from test_scripts.water_balance.combine import create_waterbalance_file

from pathlib import Path

from test_scripts.water_balance.combine import create_waterbalance_file
from test_utilities import textfiles_equal


def test_waterbalance_script(tmp_path: Path, reference_result_folder: Path):
    csv_result_file = tmp_path.joinpath("waterbalance_output.csv")

    create_waterbalance_file(
        "D:/dev/imod_coupler/tests/data/tmodel_example_output/FlowFM_his.nc",
        "D:/dev/imod_coupler/tests/data/tmodel_example_output/tot_svat_dtgw.csv",
        "D:/dev/imod_coupler/tests/data/tmodel_example_output/T-MODEL-D.LST",
        output_file_csv=csv_result_file,
    )

    csv_reference_file = reference_result_folder.joinpath(
        "test_waterbalance_script/waterbalance_output.csv"
    )
    assert textfiles_equal(csv_result_file, csv_reference_file)
