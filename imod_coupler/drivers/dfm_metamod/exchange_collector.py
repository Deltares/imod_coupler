
import abc
import os
from pathlib import Path
from typing import Any

import netCDF4 as nc
import numpy as np
from numpy.typing import NDArray


class AbstractExchange(abc.ABC):
    def __init__(self, name:str):
        pass

    def write_exchange(self, exchange: NDArray[Any], time: float, iteration: int = 0) -> None:
        pass


class NetcdfExchangeLogger(AbstractExchange):
    output_file: Path
    
    def __init__(
            self, name: str, output_dir: Path, properties: dict[str, Any]):
        if not(os.path.isdir(output_dir)):
            os.mkdir(output_dir)
        output_file = Path.joinpath(output_dir, name + '.nc')
        self.ds = nc.Dataset(output_file, "w")

    def initfile(self, ndx: int) -> None:
        self.nodedim = self.ds.createDimension('id', ndx)
        self.timedim = self.ds.createDimension('time', )
        self.timevar = self.ds.createVariable("time", "f8", ("time", ))
        self.datavar = self.ds.createVariable('xchg', "f8", ("time", "id", ))        
        self.pos = 0

    def write_exchange(
            self, exchange: NDArray[Any], time: float,
                iteration: int = 0, sync: bool = False) -> None:
        if len(self.ds.dimensions) == 0:
            self.initfile(len(exchange))
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

    def __init__(self, config: dict[str, dict[str, Any]]):
       
        general_settings = config["general"][0]
        self.output_dir = Path(general_settings["output_dir"])

        exchanges_config = config["exchanges"][0]

        self.exchanges = {}
        for exchange_name, dict_def in exchanges_config.items():           
            self.exchanges[exchange_name] = self.create_exchange_object(exchange_name, dict_def[0])

    def log_exchange(self, name: str, exchange: NDArray[Any] , time: float, iteration: int =0) -> None:
        if name not in self.exchanges.keys():
            raise ValueError(" unkwnown exchange logger: " + name)
        self.exchanges[name].write_exchange(exchange, time, iteration)

    def create_exchange_object(self, flux_name: str, dict_def: dict[str, Any])->AbstractExchange:
        typename = dict_def["type"]
        match typename:
            case "netcdf":
                return NetcdfExchangeLogger(flux_name, self.output_dir, dict_def)
            case _:
                raise ValueError("unkwnown type of exchange logger")

    def finalize(self) -> None:
        for exchange in self.exchanges.values():
            exchange.finalize()
        
        