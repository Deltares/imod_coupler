
import abc
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray


class AbstractExchange(abc.ABC):
    def __init__(self, name:str):
        pass

    def write_exchange(self, exchange: NDArray[Any], time: float, iteration: int =0)->None:
        pass

class NetcdfExchangeLogger(AbstractExchange):
    output_file: Path
    
    def __init__(self,  name:str, output_dir: Path, properties: dict[str, Any]):
        output_file = Path.joinpath(output_dir, name)


    def write_exchange(self, exchange: NDArray[Any], time: float, iteration: int =0)->None:
        pass    



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
        if not name in self.exchanges.keys():
            raise ValueError(" unkwnown exchange logger: " + name)
        self.exchanges[name].write_exchange(exchange, time, iteration)

    def create_exchange_object(self, flux_name: str, dict_def: dict[str, Any])->AbstractExchange:
        typename = dict_def["type"]
        match typename:
            case "netcdf":
                return NetcdfExchangeLogger(flux_name, self.output_dir, dict_def)
            case _:
                raise ValueError("unkwnown type of exchange logger")
        
        