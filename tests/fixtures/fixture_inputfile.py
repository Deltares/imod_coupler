import pytest_cases


@pytest_cases.fixture(scope="function")
def output_config_toml() -> str:
    '''
    returns the content of an input file for the logger.
    '''
    input_file_content = """
                        [[general]]
                        output_dir = "."

                        [[exchanges]]
                        
                        [[exchanges.example_flux_output]]
                        type = "netcdf"

                        [[exchanges.example_stage_output]]
                        type = "netcdf"
                        """
    return input_file_content
