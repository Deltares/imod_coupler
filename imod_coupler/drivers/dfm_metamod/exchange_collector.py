import abc
import os
from pathlib import Path
from typing import Any, List

import netCDF4 as nc
import numpy as np
import tomli
from numpy.typing import NDArray
from typing_extensions import Self


class AbstractExchange(abc.ABC):
    def __init__(self, name: str):
        pass

    def write_exchange(self, exchange: NDArray[Any], time: float) -> None:
        pass

    def finalize(self) -> None:
        pass


class NetcdfExchangeLogger(AbstractExchange):
    output_file: Path
    name: str

    def __init__(self, name: str, output_dir: Path, properties: dict[str, Any]):
        if not (os.path.isdir(output_dir)):
            os.mkdir(output_dir)
        output_file = Path.joinpath(output_dir, name + ".nc")
        self.ds = nc.Dataset(output_file, "w")
        self.name = name

    def initfile(self, ndx: int) -> None:
        self.nodedim = self.ds.createDimension("id", ndx)
        self.timedim = self.ds.createDimension(
            "time",
        )
        self.timevar = self.ds.createVariable("time", "f8", ("time",))
        self.datavar = self.ds.createVariable(
            "xchg",
            "f8",
            (
                "time",
                "id",
            ),
        )
        self.pos = 0

    def write_exchange(
        self, exchange: NDArray[Any], time: float, sync: bool = False
    ) -> None:
        if len(self.ds.dimensions) == 0:
            self.initfile(len(exchange))
        loc = np.where(self.timevar[:] == time)
        if np.size(loc) > 0:
            self.datavar[loc[0], :] = exchange[:]
        else:
            self.timevar[self.pos] = time
            self.datavar[self.pos, :] = exchange[:]
            self.pos += 1
        if sync:
            self.ds.sync()

    def finalize(self) -> None:
        self.ds.close()


class ExchangeCollector:
    exchanges: dict[str, AbstractExchange]
    output_dir: Path

    def __init__(self, config: dict[str, List[dict[str, Any]]]):
        general_settings = config["general"][0]
        self.output_dir = Path(general_settings["output_dir"])

        exchanges_config = config["exchanges"][0]

        self.exchanges = {}
        for exchange_name, dict_def in exchanges_config.items():
            self.exchanges[exchange_name] = self.create_exchange_object(
                exchange_name, dict_def[0]
            )

    @classmethod
    def from_file(cls, output_toml_file: str) -> Self:
        with open(output_toml_file, "rb") as f:
            toml_dict = tomli.load(f)
        return cls(toml_dict)

    def log_exchange(self, name: str, exchange: NDArray[Any], time: float) -> None:
        if name in self.exchanges.keys():
            self.exchanges[name].write_exchange(exchange, time, sync=True)

    def create_exchange_object(
        self, flux_name: str, dict_def: dict[str, Any]
    ) -> AbstractExchange:
        typename = dict_def["type"]
        if typename == "netcdf":
            return NetcdfExchangeLogger(flux_name, self.output_dir, dict_def)
        raise ValueError("unkwnown type of exchange logger")

    def finalize(self) -> None:
        for exchange in self.exchanges.values():
            exchange.finalize()
