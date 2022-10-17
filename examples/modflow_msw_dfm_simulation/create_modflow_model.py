from imod import mf6, util
import xarray as xr
import numpy as np

def create_modflow_model(idomain, top, bottom, times, workdir):

    gwf_model = mf6.GroundwaterFlowModel()

    gwf_model["ic"] = mf6.InitialConditions(head=-2.0)
    gwf_model["sto"] = mf6.SpecificStorage(1e-3, 0.1, True, 0)

    gwf_model["dis"] = mf6.StructuredDiscretization(
        idomain=idomain, top=top, bottom=bottom
    )    

    head = xr.full_like(idomain, np.nan, dtype=np.floating)
    head[:, :, 0] = 1.0  
    head[:, :, -1] = 1.0
    head = head.expand_dims(time=times)
    gwf_model["chd"] = mf6.ConstantHead(
        head, print_input=True, print_flows=True, save_flows=True
    )


    k = xr.full_like(idomain, 1, dtype=np.floating)
    gwf_model["npf"] = mf6.NodePropertyFlow(
        icelltype=idomain,
        k=k,
        variable_vertical_conductance=True,
        dewatered=False,
        perched=False,
        save_flows=True,
    )        

    gwf_model["oc"] = mf6.OutputControl(save_head="last", save_budget="last")
    # Attach it to a simulation
    simulation = mf6.Modflow6Simulation("test")
    simulation["GWF_1"] = gwf_model
    simulation.create_time_discretization(additional_times=["8/1/1971"])
    simulation["solver"] = mf6.Solution(
        modelnames=["GWF_1"],
        print_option="summary",
        csv_output=False,
        no_ptc=True,
        outer_dvclose=1.0e-4,
        outer_maximum=500,
        under_relaxation=None,
        inner_dvclose=1.0e-4,
        inner_rclose=0.001,
        inner_maximum=100,
        linear_acceleration="cg",
        scaling_method=None,
        reordering_method=None,
        relaxation_factor=0.97,
    )



    simulation.write(workdir)
    simulation.run()

    return simulation