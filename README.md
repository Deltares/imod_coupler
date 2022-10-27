# iMOD-coupler

![Continuous integration](https://github.com/Deltares/imod_coupler/workflows/Continuous%20integration/badge.svg)

The `imod_coupler` is used to couple hydrological kernels.
It currently focuses on groundwater and supports coupling between MetaSWAP, Modflow6 and dflow-FM.

It can be installed by running

```
pip install imod_coupler
```

Then you can run it as command line app via

```
imodc /path/to/imod_coupler.toml
```

In order to receive help for its usage, run

```
imodc --help
```

# Issues

Deltares colleagues can find the issue tracker at [Jira](https://issuetracker.deltares.nl/secure/RapidBoard.jspa?rapidView=469&projectKey=IMOD6&view=planning&selectedIssue=IMOD6-840)

# Contributing

In order to develop on `imod_coupler` locally, please follow the following steps:

- Download and install [miniconda](https://docs.conda.io/en/latest/miniconda.html).

- Initialize `conda` by running the following in the `Miniconda prompt`:

```
conda init
```

- Depending on your company settings, you might also have to run the following in a Powershell terminal run as administrator:

```
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned
```

- Create the environment by executing the following in your terminal:

```
conda env create --file=environment.yml
```

- Activate the environment

```
conda activate imod_coupler
```

- Install `imod_coupler` by executing (this will also put the executable `imodc` in your `PATH`):

```
pip install -e .
```

- With your Deltares credentials download
    - the [latest imod_collector](https://dpcbuild.deltares.nl/buildConfiguration/iMOD6_IMOD6collectorDaily_ReleaseX64?branch=%3Cdefault%3E&mode=builds), and 
    - the [regression imod_collector](https://dpcbuild.deltares.nl/buildConfiguration/iMOD6_IMOD6collectorDaily_ReleaseX64?branch=%3Cdefault%3E&mode=builds&tag=regression).

- Unpack the two zip files in a path of your choice and name the latest `imod_collector_devel` and the regression `imod_collector_regression`.

- Check out the MetaSWAP lookup table with your Deltares credentials which resides at `https://repos.deltares.nl/repos/DSCTestbench/trunk/cases/e150_metaswap/f00_common/c00_common/LHM2016_v01vrz`

 - To run the tests it is advisable to have a `.env` file at the root of the project directory instead of modifying global environment variables. 
 The content of `.env` would then look similar to this with the variables `IMOD_COLLECTOR_DEVEL`, `IMOD_COLLECTOR_REGRESSION` and `METASWAP_LOOKUP_TABLE` adjusted to your local machine 
 (here we assume the imod_coupler_tests project was checked out in d:\checkouts ):

```bash
IMOD_COLLECTOR_DEVEL='D:\checkouts\imod_collector_devel'
IMOD_COLLECTOR_REGRESSION='D:\checkouts\imod_collector_regression'
METASWAP_LOOKUP_TABLE='D:\checkouts\DSCtestbench\cases\e150_metaswap\f00_common\c00_common\LHM2016_v01vrz'

IMOD_COUPLER_EXEC_DEVEL='imodc' # Specify an absolute path here to use a packaged version of iMOD Coupler
IMOD_COUPLER_EXEC_REGRESSION='${IMOD_COLLECTOR_REGRESSION}/imodc.exe'
METASWAP_DLL_DEP_DIR_DEVEL='${IMOD_COLLECTOR_DEVEL}'
METASWAP_DLL_DEP_DIR_REGRESSION='${IMOD_COLLECTOR_REGRESSION}'
METASWAP_DLL_DEVEL='${IMOD_COLLECTOR_DEVEL}/MetaSWAP.dll'
METASWAP_DLL_REGRESSION='${IMOD_COLLECTOR_REGRESSION}/MetaSWAP.dll'
MODFLOW_DLL_DEVEL='${IMOD_COLLECTOR_REGRESSION}/libmf6.dll'
MODFLOW_DLL_REGRESSION='${IMOD_COLLECTOR_REGRESSION}/libmf6.dll'

DFLOW_FM_DLL='D:\checkouts\dflowfm_dll\dflowfm.dll'
DFLOW_FM_EXAMPLE_INITIAL_FILES='D:\checkouts\initial_dflowfm_files'
```

- The tests can then be run with:

```bash
pytest tests -n=auto --basetemp=tests/temp
```
