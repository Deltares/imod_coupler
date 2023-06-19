import ribasim
from imod.couplers.ribamod import RibaMod
from imod.mf6 import Modflow6Simulation


def case_ribamod_trivial_model(
    coupled_ribasim_mf6_model: Modflow6Simulation,
    ribasim_model: ribasim.Model,
) -> RibaMod:
    return RibaMod(
        ribasim_model=ribasim_model, mf6_simulation=coupled_ribasim_mf6_model
    )
