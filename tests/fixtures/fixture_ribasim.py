import pytest_cases
import ribasim
import ribasim_testmodels


@pytest_cases.fixture(scope="function")
def ribasim_bucket_model() -> ribasim.Model:
    return ribasim_testmodels.bucket_model()


@pytest_cases.fixture(scope="function")
def ribasim_backwater_model() -> ribasim.Model:
    return ribasim_testmodels.backwater_model()
