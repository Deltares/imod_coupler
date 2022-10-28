
from tempfile import tempdir
import tempfile
from pytest_cases import parametrize_with_cases
from imod_coupler.drivers.dfm_metamod.dfm_metamod import Dfm_MetaMod
from pathlib import Path
import shutil
from imod_coupler import __main__
from os import sep, listdir

testdir = tempfile.mkdtemp()

@parametrize_with_cases("dfm_metamod", prefix="case_default")
def test_dfmmetamod_initialization(dfm_metamod: Dfm_MetaMod, modflow_dll_devel: Path,
 metaswap_dll_devel: Path, metaswap_dll_dep_dir_devel: Path, dflowfm_dll :Path, dflowfm_initial_inputfiles_folder: Path):

    #write input for the simulators and a toml configuration file containing the paths of these 
    # inputfiles and the paths of the kernel dll's
    dfm_metamod.write(
        testdir,
        modflow6_dll=modflow_dll_devel,
        metaswap_dll=metaswap_dll_devel,
        metaswap_dll_dependency=metaswap_dll_dep_dir_devel,
        dflowfm_dll= dflowfm_dll
    )   


    # there are a few files that are saved in the temp directory used by the fixture 
    # by statements such as xyz_model.save() and  forcing_model.save(recurse=True).
    # However,  the DfmMetamod recreates the inputfiles in another folder usig FMModel.save()
    # and this does not produce the files created by xyz_model and  forcing_model.save
    #so as a temporary hack we copy these files into the DfmMetamod output directory
    inifiles_dir =  dflowfm_initial_inputfiles_folder
    for f in listdir(inifiles_dir):
        shutil.copy(inifiles_dir.joinpath(f), testdir + "/dflow-fm")


    inputpath  = Path(testdir  + sep + dfm_metamod._toml_name)

    #at this stage, imod_coupler is unable to complete the run with these 3 models and kernels.
    #so we check we get an exception that originates in the "couple" method - getting there
    # means the initialization of the kernels went well.  
    errmsg = "" 
    try: 
         # run the coupler given the toml configuration file
        __main__ .run_coupler(inputpath)
    except Exception as e:
         errmsg = str(e)
    assert( errmsg == "Can't find MetaSWAP\\mod2svat.inp.")