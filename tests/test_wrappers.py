import os
import shutil
from pathlib import Path

import pytest
from bmi.wrapper import BMIWrapper
from hydrolib.core.io.mdu.models import FMModel
from imod import mf6
from xmipy import XmiWrapper


@pytest.mark.skip(
    reason="currently the BMI wrapper does not survive a second initialize call"
)
def test_bmi_wrapper_can_be_initialized_and_finalized_multiple_times(
    prepared_dflowfm_model: FMModel,
    dflowfm_dll_regression: Path,
    dflowfm_initial_inputfiles_folder: Path,
    tmp_path_reg: Path,
) -> None:
    prepared_dflowfm_model.save(recurse=True)
    prepared_dflowfm_model.filepath = tmp_path_reg / "fm.mdu"
    # ================
    # modifying the path here should not be necessary
    os.environ["PATH"] = (
        os.path.dirname(str(dflowfm_dll_regression.absolute()))
        + os.pathsep
        + os.environ["PATH"]
    )
    # ================

    # there are a few files that are saved in the temp directory used by the fixture
    # by statements such as xyz_model.save() and  forcing_model.save(recurse=True).
    # However,  the DfmMetamod recreates the inputfiles in another folder usig FMModel.save()
    # and this does not produce the files created by xyz_model and  forcing_model.save
    # so as a temporary hack we copy these files into the DfmMetamod output directory
    inifiles_dir = dflowfm_initial_inputfiles_folder
    modeldir = prepared_dflowfm_model.filepath.parent
    for f in os.listdir(inifiles_dir):
        shutil.copy(inifiles_dir.joinpath(f), modeldir)

    bmiwrapper = BMIWrapper(
        engine="dflowfm", configfile=prepared_dflowfm_model.filepath
    )

    bmiwrapper.initialize()
    bmiwrapper.finalize()
    bmiwrapper.initialize()
    bmiwrapper.finalize()


def test_xmi_wrapper_can_be_initialized_and_finalized_multiple_times(
    mf6_model_with_river: mf6.Modflow6Simulation,
    modflow_dll_regression: Path,
    tmp_path_dev: Path,
) -> None:

    mf6_model_with_river.write(tmp_path_dev)
    mf6wrapper = XmiWrapper(
        lib_path=modflow_dll_regression,
        working_directory=tmp_path_dev,
    )
    mf6wrapper.initialize()
    mf6wrapper.finalize()
    mf6wrapper.initialize()
    mf6wrapper.finalize()
