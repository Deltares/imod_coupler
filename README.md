# iMOD Coupler

`imod_coupler` couples hydrological kernels. It currently focuses on groundwater and supports coupling between MetaSWAP, MODFLOW 6, and Ribasim.

It is a command-line application that can be run via:

```sh
imodc /path/to/imod_coupler.toml
```

For usage information, run:

```sh
imodc --help
```

## Issues

Deltares colleagues can find the issue tracker on [Jira](https://issuetracker.deltares.nl/secure/RapidBoard.jspa?rapidView=469&projectKey=IMOD6&view=planning&selectedIssue=IMOD6-840).

## Contributing

### Setting up your machine

To develop `imod_coupler` locally:

1. Download and install [pixi](https://pixi.sh).
2. Clone the repository and navigate to the project root.
3. Create the development environment:

   ```sh
   pixi install -e dev
   ```

4. Setup the test dependencies:

   ```sh
   pixi run -e dev setup-test-dependencies
   ```

   This command:
   - Downloads the kernel dependencies (MetaSWAP, MODFLOW 6 & Ribasim) and the [regression imod_coupler](https://github.com/Deltares/imod_coupler/releases)
   - Downloads the [MetaSWAP lookup table](https://s3.deltares.nl/metaswap/db/LHM2016_v01vrz/)
   - Generates a `.env` file in the project root with environment variables pointing to the downloaded binaries in the `.pixi` folder

5. Run the tests:

   ```sh
   pixi run -e dev tests
   ```

6. Lint the codebase:

   ```sh
   pixi run -e dev lint
   ```

> **Tip:** When developing with Visual Studio Code, open the project via `open-vscode.bat` to launch a new window with the correct environment variables set.

### Running acceptance tests

The user acceptance tests currently use [the LHM model](https://nhi.nu/modellen/lhm/). More models may be added in the future. These tests can only be run locally on Windows.

1. Pull the data from the Minio/DVC remote:

   ```sh
   pixi run -e user-acceptance fetch_lhm
   ```

   This unpacks the LHM model data and the MetaSWAP database required for the tests.

2. Run the user acceptance tests:

   ```sh
   pixi run -e user-acceptance user_acceptance_test
   ```

   The tests take approximately 60 minutes to complete.

### DVC

Various versions of test data are tracked using DVC, which allows different data versions to exist across branches. The storage bucket is read-only for the public. To push new or updated data, contact one of the project maintainers.

### Debugging

When debugging unit tests in Visual Studio Code using the Test Explorer, you may encounter issues because MODFLOW 6 and MetaSWAP can behave unpredictably when initialized and finalized multiple times in the same process.

This does not occur when running (not debugging) unit tests, because a conditional check determines whether to call `subprocess.run()` or stay within the main thread. See the `run_coupler_function` fixture for details.

### Troubleshooting

If you encounter errors after pulling the latest changes, your pip dependencies may be outdated. Update them by running:

```sh
pixi run update-git-dependencies
```

### Creating a release

1. Update the version number in `imod-coupler/__init__.py`.

2. Update the version number in `pre-processing/primod/__init__.py`.

3. Add all notable changes to the `[Unreleased]` section in [CHANGELOG.md](CHANGELOG.md), using the existing subsections (Added, Fixed, Changed, Removed).

4. In CHANGELOG.md, rename `## [Unreleased]` to `## [vYYYY.MM.X]` and add a fresh empty `## [Unreleased]` section above it:

   ```markdown
   ## [Unreleased]

   ### Added

   ### Fixed

   ### Changed

   ### Removed

   ## [vYYYY.MM.X]
   ...
   ```

   You can verify the notes that will be used for the release with:

   ```sh
   python scripts/extract_changelog_notes.py vYYYY.MM.X
   ```

5. Commit the changelog and the init file updates:

   ```sh
   git add CHANGELOG.md imod_coupler/__init__.py pre-processing/primod/__init__.py 
   git commit -m "Release vYYYY.MM.X"
   ```

6. When the commit has been merged to main or a release branch, switch to that branch and tag the commit:

   ```sh
   git tag vYYYY.MM.X
   ```

7. Push the tag:

   ```sh
   git push origin vYYYY.MM.X
   ```

8. In TeamCity, select the **Deploy** project and trigger the **Deploy All** build, selecting the tag `vYYYY.MM.X` as the branch. TeamCity will build the artifacts and create the GitHub release using the notes from CHANGELOG.md.
