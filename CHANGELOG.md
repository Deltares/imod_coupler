# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

### Fixed

### Changed

### Removed

## [v2026.6.0]

### Added
- Add continue logic for non-converging coupled simulations: when MODFLOW 6
  `CONTINUE` is set in `mfsim.nam`, the coupler logs a warning instead of
  raising an error on non-convergence
- Add user acceptance test to CI pipeline
- Add SonarQube buildstep to TeamCity pipeline
- Add Deploy pipeline to TeamCity (PyPI publishing and GitHub releases)
- Add pixi update build to TeamCity

### Fixed
- Fix silent crash when encountered an exception during unit tetst
- Fix exchange logger not being closed after ribametamod run, causing file
  lock errors on Windows

### Changed
- Update Ribasim to version v2026.1.1
- Update MetaSWAP to version v9.0
- Update MODFLOW6 to version 6.7.0
- Rename `install-*` tasks to `fetch-*` in `pixi.toml` to better reflect
  that these tasks download binaries rather than install packages
- Rename `install-test-dependencies` to `setup-test-dependencies`


## [v2025.11.0]

### Changed

- Update Ribasim to version 2025.6
- Update MODFLOW6 to version 6.6.3
- Update iMOD Python to version 1.0.0
- Primod: Allow grid based basin and water user definitions and facilitate subsetting of subgrid-df
- Ribasim-MetaSWAP coupling: Pass MetaSWAP timestep to `update_ribasim`

## [v2024.4.0]

### Added

- First imod_coupler release involving a Ribasim-MetaSWAP-MODFLOW6 (RibaMetaMod) implementation

## [v2024.3.0]

### Added

- Add ponding
- Add formal RibaMetaMod tests
- Add cron job to update pixi lock file every month

### Fixed

- Additionally check if columns are in data frame
- Fix primod `RchSvatMapping` layer dimension (#262)
- Fix name changes of Ribasim variables in `get_value_ptr` statements
- Deal with potential time axis in conductance
- Call `add_api_package` to mf6 model
- Do not overwrite drainage and infiltration values of uncoupled basins
- Set drainage and infiltration to NA for basins coupled to MODFLOW
- Call `update_bottom_minimum`

### Changed

- Update numerical scheme for RibaMetaMod
- Adapt to changes in Ribasim API
- Move from `requests` to `httpx`
- Update to pydantic 2.0 validators syntax
- Move `basin_definition` from RibaMod to DriverCoupling
- Refactor DriverCoupling
- Check time of Ribasim and MODFLOW6 model before coupling
- Improve debugging in Visual Studio Code
- Auto install test dependencies

## [v2024.01.2]

### Fixed

- Compute budget in a better way; take new fid index into account
- Fix changes required to get a real coupled model running

### Changed

- Start logging Ribasim version again

## [v2024.01.1]

### Added

- Add pixi task to publish primod
- Add docs for DriverCoupling

### Changed

- Refactor and activate exchanges for active coupling
- Use `ribasim-api`: `update_subgrid_level`
- Add two-basin test models

## [v2024.01.0]

### Added

- Create RibaMetaMod as a copy of RibaMod
- Add pixi
- Add MetaMod functionality to RibaMetaMod
- Add sprinkling exchange MetaSWAP-Ribasim
- Add temporary RibaMetaMod test
- Add more ruff rules
- Optional kernels

### Changed

- Update to newest Ribasim Python API
- Remove pydantic config `arbitrary_types_allowed`
- Change memory address for wells and refactor retrieving the pointer
- Move to hatchling as build backend

## [v2023.08.0]

### Added

- Add initial version of RibaMod
- Add conversion between time units of Ribasim and MODFLOW6
- Add minimal conda environment for building the executable
- Move coupling pre-processing from iMOD Python to primod

### Fixed

- No convergence in MODFLOW6 no longer results in an error

### Changed

- Refactor kernel wrappers
- Refactor logging
- Move docs to iMOD Suite Documentation
- Adapt to newest MODFLOW6 version
- Remove unnecessary config dir parameter

## [v0.11.0]

### Added

- Moved testbench to pytest, enabling integration and unit tests and making it possible to run tests locally

### Changed

- Moved to new configuration file format
- Added concept of "drivers"
