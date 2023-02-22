import os
from pathlib import Path

import netCDF4 as nc
import numpy as np
import tomli
from numpy.typing import NDArray

from imod_coupler.drivers.dfm_metamod.exchange_collector import ExchangeCollector


def test_exchange_collector_read(tmp_path_dev: Path) -> None:
    input_file_content = """
                        [[general]]
                        output_dir = "."

                        [[exchanges]]
                        
                        [[exchanges.mf-ridv2dflow1d_flux_output]]
                        type = "netcdf"
                        postfix = "in"

                        [[exchanges.dflow1d2mf-riv_stage_output]]
                        type = "netcdf"
                        postfix = "out"
                        """
    config_dict = tomli.loads(input_file_content)
    exchange_collector = ExchangeCollector(config_dict)

    some_array0: NDArray[np.float_] = NDArray[np.float_](
        (5,), buffer=np.array([1.1, 2.0, -4.8, np.nan, 3])
    )
    some_array1: NDArray[np.float_] = NDArray[np.float_](
        (5,), buffer=np.array([1.1, 666.0, -4.8, 0.0, 3])
    )
    exchange_collector.log_exchange("mf-ridv2dflow1d_flux_output", some_array0, 8.0)
    exchange_collector.log_exchange("mf-ridv2dflow1d_flux_output", some_array1, 23.0)
    exchange_collector.finalize()

    ds = nc.Dataset("./mf-ridv2dflow1d_flux_output.nc", "r")
    dat = ds.variables['xchg'][:]
    tim = ds.variables['time'][:]
    assert np.array_equal(dat[0, :], some_array0, equal_nan=True)
    assert np.array_equal(dat[1, :], some_array1, equal_nan=True)
    assert np.array_equal(tim[:], np.array([8.0, 23.0]), equal_nan=True)



