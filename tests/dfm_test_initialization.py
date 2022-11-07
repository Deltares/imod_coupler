import os
import shutil
from pathlib import Path


def copy_inputfiles(
    dfm_files_dir: Path,
    tempdir: Path,
) -> None:

    """
    there are a few files that are saved in the temp directory used by the fixture
    by statements such as xyz_model.save() and  forcing_model.save(recurse=True).
    However,  the DfmMetamod recreates the inputfiles in another folder usig FMModel.save()
    and this does not produce the files created by xyz_model and  forcing_model.save
    so as a temporary hack we copy these files into the DfmMetamod output directory
    """

    for f in os.listdir(dfm_files_dir):
        shutil.copy(dfm_files_dir.joinpath(f), tempdir)


def set_dfm_path(dflowfm_dll_regression: Path) -> None:

    os.environ["PATH"] = (
        os.path.dirname(str(dflowfm_dll_regression.absolute()))
        + os.pathsep
        + os.environ["PATH"]
    )
