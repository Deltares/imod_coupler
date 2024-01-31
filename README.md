# iMOD Coupler

The `imod_coupler` is used to couple hydrological kernels.
It currently focuses on groundwater and supports coupling between MetaSWAP and Modflow6.

It can be installed by running

```sh
pip install imod_coupler
```

Then you can run it as command line app via

```sh
imodc /path/to/imod_coupler.toml
```

In order to receive help for its usage, run

```sh
imodc --help
```

## Issues

Deltares colleagues can find the issue tracker at [Jira](https://issuetracker.deltares.nl/secure/RapidBoard.jspa?rapidView=469&projectKey=IMOD6&view=planning&selectedIssue=IMOD6-840)

## Contributing

In order to develop on `imod_coupler` locally, please follow the following steps:

- Create an access token at the [TeamCity build server](https://dpcbuild.deltares.nl/profile.html?item=accessTokens#).
- Store the token in your local user environment as `TEAMCITY_TOKEN`.
  This token will be used to download artifacts from Teamcity, make sure to store it well.
- Download and install [pixi](https://prefix.dev/docs/pixi/overview).
- Download the Git repository of `imod_coupler` and navigate to the root of the project.
- Create the environment by executing the following in your terminal:

  ```sh
  pixi run install
  ```

- Install the test dependencies by executing the following in your terminal.
  It automatically downloads the [latest imod_collector](https://dpcbuild.deltares.nl/buildConfiguration/iMOD6_IMOD6collectorDaily_ReleaseX64?branch=%3Cdefault%3E&mode=builds) and [regression imod_collector](https://dpcbuild.deltares.nl/buildConfiguration/iMOD6_IMOD6collectorDaily_ReleaseX64?branch=%3Cdefault%3E&mode=builds&tag=regression) from the build server.
  It downloads the [MetaSWAP lookup table](https://repos.deltares.nl/repos/DSCTestbench/trunk/cases/e150_metaswap/f00_common/c00_common/LHM2016_v01vrz).
  It also generates a `.env` that contains the paths to the downloaded imod_collectors.

  ```sh
  pixi run install-test-dependencies
  ```

- To run the tests it is advisable to have a `.env` file at the root of the project directory instead of modifying global environment variables. 
 The content of `.env` would then look similar to this with the variables `IMOD_COLLECTOR_DEVEL`, `IMOD_COLLECTOR_REGRESSION` and `METASWAP_LOOKUP_TABLE` adjusted to your local machine:

  ```sh
  IMOD_COLLECTOR_DEVEL='D:\checkouts\imod_collector_devel'
  IMOD_COLLECTOR_REGRESSION='D:\checkouts\imod_collector_regression'
  METASWAP_LOOKUP_TABLE='D:\checkouts\DSCtestbench\cases\e150_metaswap\f00_common\c00_common\LHM2016_v01vrz'

  # Specify an absolute path here to use a packaged version of iMOD Coupler
  IMOD_COUPLER_EXEC_DEVEL='imodc'
  IMOD_COUPLER_EXEC_REGRESSION='${IMOD_COLLECTOR_REGRESSION}/imod_coupler/imodc.exe'
  METASWAP_DLL_DEP_DIR_DEVEL='${IMOD_COLLECTOR_DEVEL}/metaswap'
  METASWAP_DLL_DEP_DIR_REGRESSION='${IMOD_COLLECTOR_REGRESSION}/metaswap'
  METASWAP_DLL_DEVEL='${IMOD_COLLECTOR_DEVEL}/metaswap/MetaSWAP.dll'
  METASWAP_DLL_REGRESSION='${IMOD_COLLECTOR_REGRESSION}/metaswap/MetaSWAP.dll'
  MODFLOW_DLL_DEVEL='${IMOD_COLLECTOR_DEVEL}/modflow6/libmf6.dll'
  MODFLOW_DLL_REGRESSION='${IMOD_COLLECTOR_REGRESSION}/modflow6/libmf6.dll'
  RIBASIM_DLL_DEP_DIR_DEVEL='${IMOD_COLLECTOR_DEVEL}/ribasim/bin'
  RIBASIM_DLL_DEP_DIR_REGRESSION='${IMOD_COLLECTOR_REGRESSION}/ribasim/bin'
  RIBASIM_DLL_DEVEL='${IMOD_COLLECTOR_DEVEL}/ribasim/bin/libribasim.dll'
  RIBASIM_DLL_REGRESSION='${IMOD_COLLECTOR_REGRESSION}/ribasim/bin/libribasim.dll'
  ```

- The tests can then be run with:

  ```sh
  pixi run tests
  ```

- Lint the codebase with:

  ```sh
  pixi run lint
  ```

- When developing with visual studio code, it is recommended to open the application via `open-vscode.bat`.
  This will open the application in a new vscode window with the correct environment variables set.

### Debugging

When debugging the unit tests in visual studio code with the test explorer, you can encounter some problems.
Both MODFLOW 6 and MetaSWAP might behave unpredicateble when being initialized and finalized multiple times.

When you only run, not debug, unit tests, this is not the case, since there is a switch statement that determines if we should call `subprocess.run()`, or stay within the main thread.
See the fixture for `run_coupler_function` for more information.

### Troubleshooting

If you encounter errors while running the tests, it might be that your pip dependencies are outdated.
This happens when you have pulled the latest changes from imod_coupler.
In that case you need to update the pip dependencies as well.
Try running:

```sh
pixi run update-git-dependencies
```
