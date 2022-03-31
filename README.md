# iMOD-coupler

![Continuous integration](https://github.com/Deltares/imod_coupler/workflows/Continuous%20integration/badge.svg)

The `imod_coupler` is used to couple hydrological kernels.
It currently focuses on groundwater and supports coupling between MetaSWAP and Modflow6.

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

In order to develop on `imod_coupler` locally, execute the following line inside your virtual environment

```bash
pip install -e ".[tests, lint, docs]"
```
