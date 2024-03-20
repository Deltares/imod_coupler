from imod.mf6 import Modflow6Simulation
from imod.msw import MetaSwapModel
from primod import MetaMod, MetaModDriverCoupling


def case_sprinkling(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> MetaMod:
    driver_coupling = MetaModDriverCoupling(
        mf6_model="GWF_1", mf6_recharge_package="rch_msw", mf6_wel_package="wells_msw"
    )
    return MetaMod(
        prepared_msw_model,
        coupled_mf6_model,
        coupling_list=[driver_coupling],
    )
