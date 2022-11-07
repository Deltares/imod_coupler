import os
import shutil
from pathlib import Path

import pytest
from hydrolib.core.io.mdu.models import FMModel

from imod_coupler.drivers.dfm_metamod.extended_bmi_wrapper import ExtendedBMIWrapper


@pytest.mark.skip(
    reason="currently the BMI wrapper does not survive a second initialize call, and it was already used in test_dfm_metamod"
    + "It should still work when running just this test."
)
def test_get_river_stage_from_dflow(
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

    bmiwrapper = ExtendedBMIWrapper(
        engine="dflowfm", configfile=prepared_dflowfm_model.filepath
    )

    bmiwrapper.initialize()
    water_levels_1d = bmiwrapper.get_waterlevels_1d()
    bmiwrapper.finalize()

    # the current test dataset does not have 1d rivers.
    assert len(water_levels_1d) == 0
