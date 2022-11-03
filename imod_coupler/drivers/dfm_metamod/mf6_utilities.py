import numpy as np
from imod import mf6
from imod.mf6 import GroundwaterFlowModel, Modflow6Simulation
from numpy.typing import NDArray
from xmipy import XmiWrapper


class MF6Utilities:
    @classmethod
    def get_flow_models(
        cls, mf6_simulation: Modflow6Simulation
    ) -> list[GroundwaterFlowModel]:
        return [
            model
            for _, model in mf6_simulation.items()
            if isinstance(model, GroundwaterFlowModel)
        ]

    @classmethod
    def get_modflow_package_keys(
        cls, mf6_flow_model: GroundwaterFlowModel, package_type: type
    ):
        return [
            pkgname for pkgname, pkg in mf6_flow_model if isinstance(pkg, package_type)
        ]

    @classmethod
    def set_river_stages(
        cls,
        mf6_wrapper: XmiWrapper,
        mf6_model: Modflow6Simulation,
        new_river_stages: NDArray[np.float_],
    ):
        flow_models = cls.get_flow_models(mf6_model)
        if len(flow_models) > 1:
            raise ValueError("Currently we support only one flow model.")

        river_pack_keys = cls.get_modflow_package_keys(flow_models[0], mf6.River)
        if len(river_pack_keys) > 1:
            raise ValueError("Currently we support only one river package.")
        bound_adress = mf6_wrapper.get_var_address("BOUND", "GWF_1", "Oosterschelde")
        bound = mf6_wrapper.get_value_ptr(bound_adress)
        stage = bound[:, 0]
        if len(new_river_stages) != len(stage):
            raise ValueError(f"Expected size of new_river stages is {len(stage)}")
        stage[:] = new_river_stages[:]
