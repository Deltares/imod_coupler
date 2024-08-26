# iMOD Coupler

The `imod_coupler` is used to couple hydrological kernels.
It currently focuses on groundwater and supports coupling between MetaSWAP and Modflow6.

It as command line app that can be run via

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
  Choose permission scope: `<Same as current user>`.
- Store the token in your local user environment as `TEAMCITY_TOKEN`.
  This token will be used to download artifacts from Teamcity, make sure to store it well.
- Download and install [pixi](https://pixi.sh).
- Download and install [svn](https://tortoisesvn.net/downloads.html).
  Make sure to install the svn command line tools as well.
- Download the Git repository of `imod_coupler` and navigate to the root of the project.
- Create the environment by executing the following in your terminal:

  ```sh
  pixi run --environment=dev install
  ```

- Install the test dependencies by executing the following in your terminal.
  It automatically downloads the [latest imod_collector](https://dpcbuild.deltares.nl/buildConfiguration/iMOD6_IMOD6collectorDaily_ReleaseX64?branch=%3Cdefault%3E&mode=builds) and [regression imod_collector](https://dpcbuild.deltares.nl/buildConfiguration/iMOD6_IMOD6collectorDaily_ReleaseX64?branch=%3Cdefault%3E&mode=builds&tag=regression) from the build server.
  It downloads the [MetaSWAP lookup table](https://repos.deltares.nl/repos/DSCTestbench/trunk/cases/e150_metaswap/f00_common/c00_common/LHM2016_v01vrz).
  It also generates a `.env` that contains the paths to the downloaded imod_collectors.

  ```sh
  pixi run install-test-dependencies
  ```

  `install-test-dependencies` creates a `.env` file in the root of the project with the required environment variables pointing to the paths of imod_collector that can be found in the `.pixi` folder.

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


##coupling imod-coupler and imod python metsawap regridding branch:


1) create imod_suite directory
2) in it, create a subdirectory imod_coupler and a subdirectory imod-python.
3) check out both projects in their own directory. For imod-python, make sure to 
check out the metaswap_regridding_feature branch or a development branch forked from it.
for imod_coupler check out "coupler_regrid_feature_branch" or a development branch forked from it.

4) in the imod suite directory, create a batch file that will overwrite the coupler's 
pixi install of imod with the branch we have checked out in the imod-python directory.
This is done for each pixi environment. Assuming  we have 2, the batch file looks like this.


xcopy  /e /k /h /i  imod-python\imod imod_coupler\.pixi\envs\default\Lib\site-packages\imod
xcopy  /e /k /h /i imod-python\imod imod_coupler\.pixi\envs\dev\Lib\site-packages\imod 


The batch file will overwrite the pixi install( in .pixi\envs\default\Lib\site-packages\imod) with whatever
is checked out locally in the imod-python folder.