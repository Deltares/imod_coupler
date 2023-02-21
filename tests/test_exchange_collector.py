import numpy as np
import tomli
from numpy.typing import NDArray

from imod_coupler.drivers.dfm_metamod.exchange_collector import ExchangeCollector


def test_exchange_collector_read() -> None:
    input_file_content = """
                        [[general]]
                        output_dir = "."

                        [[exchanges]]
                        
                        [[exchanges.mf-ridv2dflow1d_flux_output]]
                        type = "netcdf"

                        [[exchanges.dflow1d2mf-riv_stage_output]]
                        type = "netcdf"
                        """

    config_dict = tomli.loads(input_file_content)
    exchange_collector = ExchangeCollector(config_dict)

    some_array: NDArray[np.float_] = NDArray[np.float_](
        (5,), buffer=np.array([1.1, 2.0, -4.8, np.nan, 3])
    )
    exchange_collector.log_exchange("mf-ridv2dflow1d_flux_output", some_array, 8.0)
