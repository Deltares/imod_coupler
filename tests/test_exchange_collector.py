import os
from pathlib import Path

import netCDF4 as nc
import numpy as np
import pytest
import tomli
from numpy.typing import NDArray

from imod_coupler.drivers.dfm_metamod.exchange_collector import ExchangeCollector


def test_exchange_collector_read(tmp_path_dev: Path, output_config_toml: str) -> None:
    cwd0 = os.getcwd()
    if not (os.path.isdir(tmp_path_dev)):
        os.makedirs(tmp_path_dev)
    os.chdir(tmp_path_dev)

    try:
        config_dict = tomli.loads(output_config_toml)
        config_dict["general"][0]["output_dir"] = tmp_path_dev
        exchange_collector = ExchangeCollector(config_dict)

        some_array0: NDArray[np.float_] = NDArray[np.float_](
            (5,), buffer=np.array([1.1, 2.0, -4.8, np.nan, 3])
        )
        some_array1: NDArray[np.float_] = NDArray[np.float_](
            (5,), buffer=np.array([1.1, 666.0, -4.8, 0.0, 3])
        )
        exchange_collector.log_exchange("example_flux_output", some_array0, 8.0)
        exchange_collector.log_exchange("example_flux_output", some_array1, 23.0)
        exchange_collector.finalize()

        ds = nc.Dataset(tmp_path_dev / "example_flux_output.nc", "r")
        dat = ds.variables["xchg"][:]
        tim = ds.variables["time"][:]
        assert np.array_equal(dat[0, :], some_array0, equal_nan=True)
        assert np.array_equal(dat[1, :], some_array1, equal_nan=True)
        assert np.array_equal(tim[:], np.array([8.0, 23.0]), equal_nan=True)
    finally:
        os.chdir(cwd0)


def test_exchange_collector_ignores_unknown_exchanges(
    tmp_path_dev: Path, output_config_toml: str
) -> None:
    config_dict = tomli.loads(output_config_toml)
    config_dict["general"][0]["output_dir"] = tmp_path_dev
    exchange_collector = ExchangeCollector(config_dict)

    some_array0: NDArray[np.float_] = NDArray[np.float_](
        (5,), buffer=np.array([1.1, 2.0, -4.8, np.nan, 3])
    )
    some_array1: NDArray[np.float_] = NDArray[np.float_](
        (5,), buffer=np.array([1.1, 666.0, -4.8, 0.0, 3])
    )
    exchange_collector.log_exchange("non_existing_type", some_array0, 8.0)
    exchange_collector.log_exchange("non_existing_type", some_array1, 23.0)
    exchange_collector.finalize()


def test_exchange_collector_raises_exception_when_array_size_varies(
    tmp_path_dev: Path, output_config_toml: str
) -> None:
    config_dict = tomli.loads(output_config_toml)
    config_dict["general"][0]["output_dir"] = tmp_path_dev
    exchange_collector = ExchangeCollector(config_dict)

    some_array: NDArray[np.float_] = NDArray[np.float_](
        (5,), buffer=np.array([1.1, 2.0, -4.8, np.nan, 3])
    )
    some_smaller_array: NDArray[np.float_] = NDArray[np.float_](
        (4,), buffer=np.array([1.1, 666.0, -4.8, 0.0])
    )
    exchange_collector.log_exchange("example_stage_output", some_array, 8.0)
    with pytest.raises(ValueError) as e:
        exchange_collector.log_exchange(
            "example_stage_output", some_smaller_array, 23.0
        )
    assert (
        "operands could not be broadcast together with remapped shapes "
        + "[original->remapped]: (4,)  and requested shape (1,5)"
        in str(e.value)
    )
    exchange_collector.finalize()


def test_exchange_collector_overwrites_when_time_is_repeated(
    tmp_path_dev: Path, output_config_toml: str
) -> None:
    config_dict = tomli.loads(output_config_toml)
    config_dict["general"][0]["output_dir"] = tmp_path_dev
    exchange_collector = ExchangeCollector(config_dict)

    some_arrays: list[NDArray[np.float_]] = [
        NDArray[np.float_]((5,), buffer=np.array([1.1, 2.0, -4.8, np.nan, 1])),
        NDArray[np.float_]((5,), buffer=np.array([1.1, 2.2, -5.8, np.nan, 2])),
        NDArray[np.float_]((5,), buffer=np.array([1.1, 2.0, 8.8, np.nan, 3])),
        NDArray[np.float_]((5,), buffer=np.array([1.5, 8.0, 2.8, 6.0, -3])),
    ]

    exchange_collector.log_exchange("example_stage_output", some_arrays[0], 8.0)
    exchange_collector.log_exchange("example_stage_output", some_arrays[1], 9.0)
    exchange_collector.log_exchange("example_stage_output", some_arrays[2], 10.0)
    exchange_collector.log_exchange("example_stage_output", some_arrays[3], 9.0)
    exchange_collector.finalize()

    ds = nc.Dataset(tmp_path_dev / "example_stage_output.nc", "r")
    dat = ds.variables["xchg"][:]
    tim = ds.variables["time"][:]
    assert np.array_equal(dat[1, :], some_arrays[3], equal_nan=True)
    assert np.array_equal(tim[:], np.array([8.0, 9.0, 10.0]), equal_nan=True)
