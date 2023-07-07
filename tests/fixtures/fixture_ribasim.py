import pytest_cases
import ribasim
import ribasim_testmodels


@pytest_cases.fixture(scope="function")
def ribasim_model() -> ribasim.Model:
    return ribasim_testmodels.bucket_model()
