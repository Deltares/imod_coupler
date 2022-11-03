import math
import os
import shutil
import tempfile
from pathlib import Path

from bmi.wrapper import BMIWrapper
from hydrolib.core.io.bc.models import ForcingModel
from hydrolib.core.io.mdu.models import FMModel
from imod import mf6
from xmipy import XmiWrapper


def test_get_river_stage_from_dflow(
    prepared_dflowfm_model: FMModel,
    dflowfm_dll_regression: Path,
    dflowfm_initial_inputfiles_folder: Path,
    tmp_path_reg: Path,
):

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
    nr_nodes = bmiwrapper.get_var("ndxi")  # number of 1d cells
    nr_nodes2d = bmiwrapper.get_var("ndx2d")  # number of 2d cells
    nr_nodes1d = nr_nodes - nr_nodes2d
    waterlevels = bmiwrapper.get_var("s1")
