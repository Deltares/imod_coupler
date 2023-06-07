from imod.couplers.ribametamod import RibaMetaMod
from imod.mf6 import Modflow6Simulation
from imod.msw import MetaSwapModel


def case_sprinkling(
    coupled_mf6_model: Modflow6Simulation,
    prepared_msw_model: MetaSwapModel,
) -> RibaMetaMod:
    return RibaMetaMod(
        prepared_msw_model,
        coupled_mf6_model,
        mf6_rch_pkgkey="rch_msw",
        mf6_wel_pkgkey="wells_msw",
    )
