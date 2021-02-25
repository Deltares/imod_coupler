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

## Configuration file

The configuration file is necessary to describe the model and its dependencies.
It is in the [toml](https://toml.io/en/) format and should have a `.toml` extension. 

Note that `toml` uses quote marks differently than `python`. Single quotes in toml (`''`) are interpreted similarly to how python would interpret a rawstring (`r''` or `r""`), whereas double quotes (`""`) are interpreted in a similar manner to regular strings in python (`""` or `''`). This matters for paths on Windows, for which we advice to use single quotes.

```toml
# This is a configuration file for the imod_coupler
# Relative paths are interpreted as relative to the configuration file path

[kernels]
    [kernels.modflow6]
    dll = '/path/to/libmf6.dll'
    model = '.'

    [kernels.metaswap]
    dll = '/path/to/MetaSWAP.dll'
    model = './GWF_1/MSWAPINPUT'
    dll_dependency = '/path/to/MPICHDLL'


[[exchanges]]
# Two kernels per exchange
kernels = ['modflow6', 'metaswap']

```

## Technical Reference

A technical explanation can be found [here](TECHNICAL.md).

## Known Issues
### Release v0.9.0 
_FileNotFoundError: Could not find module "\path\to\MetaSWAP.dll" (or one of its dependencies). Try using the full path with constructor syntax._
This is caused by not having the Intel redistrutable libraries on the system. They can be installed from https://software.intel.com/content/www/us/en/develop/articles/intel-compilers-redistributable-libraries-by-version.html. Make sure to choose the correct platform and the version for 'Parallel Studio XE 2018'. (We are working on removing this dependency for future releases)
