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
  pixi install --environment=dev
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

- When developing with visual studio code, it is recommended to open the
  application via `open-vscode.bat`. This will open the application in a new
  vscode window with the correct environment variables set.

- How to run the user acceptance tests will be described below. The model
  currently used for the user acceptance tests is [the LHM
  model](https://nhi.nu/modellen/lhm/), but more models might be added in the
  future.

  Run the user acceptance tests locally on a Windows machine by following these
  steps:

  1. First contact imod.support@deltares.nl and ask for an access key to access
    the iMOD Coupler test data. They will contact you and send you a key. Make
    sure you don't share this key with others!
  2. Activate the user acceptance environment by running the following command in the root
    of the repository:
    
    ```sh
    pixi shell -e user-acceptance
    ```

  3. Add your key to the DVC configuration by running the following command in the root
    of the repository:

    ```sh
      dvc remote modify --local minio access_key_id <your_access_key>
      dvc remote modify --local minio secret_access_key <your_secret_access_key>
    ```

    Don't forget the ``--local`` flag, as this will store the key in the
    ``.dvc/config.local`` file, which is not committed to the repository.

  4. Pull the data from the DVC remote by running the following command in the root
    of the repository:

    ```sh
      pixi run fetch_lhm
    ```

    This will unpack the LHM model data, which is used in the user acceptance
    tests.

  5. To make the MetaSWAP lookup table available to the user acceptance tests, you need to
    mount the MinIO bucket containing the lookup table to a local folder.
  
    First the right software needs to be installed. On Windows, you can use
    [Chocolatey](https://chocolatey.org/) to install WinFSP and rclone by
    running the following commands:

    ```sh
    choco install winfsp
    choco install rclone
    ```

    Configure rclone to access the Deltares MinIO server. You can use the same
    access key and secret access key as used for DVC:

    ```sh
    rclone config
    ```

    Your rclone.conf file should look like as follows. Note that in this case
    the remote is named ``minio``:

    ```
    [minio]
    type = s3
    provider = Minio
    access_key_id = <your_access_key>
    secret_access_key = <your_secret_access_key>
    endpoint = https://s3.deltares.nl
    acl = private
    location_constraint = EU
    region = eu-west-1
    ```

    After configuring rclone, you can mount the MinIO bucket containing the
    MetaSWAP lookup table by running the following command in the root of the
    repository.

    ```sh
      pixi run mount_minio
    ```

    This runs as a background process, so it is expected that it doesn't finish.
    The next step therefore needs to be conducted **in a separate process**.

  6. Run the user acceptance tests by running the following command in the root 
    of the repository **in a separate process**. Note that the MetaSWAP database
    is read from an S3 bucket, which requires fast network access. Running the
    test on WiFi will slow down the tests significantly (1.5 hour instead of 45
    minutes).

    ```sh
      pixi run -e user-acceptance user_acceptance_test
    ```

    The test should take about 45 minutes to complete.

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
