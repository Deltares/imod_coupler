from ribasim_api import RibasimApi
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import os

modeldir = "c:/pytest/pytest-1591/test_ribametamod_bucket_bucket0/develop/"
os.chdir(modeldir)

riba_path:Path = Path("d:/leander/imod_collector/ribasim/bin")    # path to the ribasim library
ribasim: RibasimApi     # the Ribasim model instance

riba = RibasimApi(
                lib_path = riba_path / "libribasim.dll",
                lib_dependency = riba_path,
                timing=False)

ribasim_config_file = "ribasim/ribasim.toml"

# Initialize ribasim config
riba.init_julia()
riba.initialize(ribasim_config_file)

# Get all relevant Ribasim pointers
ribasim_infiltration = riba.get_value_ptr("basin.infiltration")
ribasim_drainage = riba.get_value_ptr("basin.drainage")
ribasim_infiltration_integrated = riba.get_value_ptr("basin.infiltration_integrated")
ribasim_infiltration_save = np.empty_like(ribasim_infiltration_integrated)
ribasim_drainage_integrated = riba.get_value_ptr("basin.drainage_integrated")
ribasim_drainage_save = np.empty_like(ribasim_drainage_integrated)
ribasim_level = riba.get_value_ptr("basin.level")
ribasim_storage = riba.get_value_ptr("basin.storage")
ribasim_user_demand = riba.get_value_ptr("user_demand.demand")
ribasim_user_realized = riba.get_value_ptr("user_demand.realized")
ribasim_user_realized_save = np.empty_like(ribasim_user_realized)
# ----------------------------------------------------------------------------------
current_time = 0
day2sec = 86400.
infilt = [12, 0, 12, 0, 4, 6, 0, 0, 0,14,16,18]
drain =  [ 0,10, 0, 10, 4, 6, 8,10,12, 0, 0, 0]

calculated = [] # calculated infiltration over a day
expected = [] # expected infiltration over a day

# read forcing from file
infilt = []
drain = []
fdmp = open("dump.txt","r")
input = fdmp.readlines()

for s in input:
    (inl,drn) = [float(ss) for ss in s.split()]
    infilt.append(inl*day2sec)
    drain.append(drn*day2sec)

# read forcing from file
infilt = []
drain = []
inl = 0.00
drn = 25.0
for i in range(300):
#   infilt.append(inl)
#   drain.append(drn)
    infilt.append(0.0)
    drain.append(drn-inl)
    (inl,drn) = (drn,inl)

# test section
for inl, drn in zip(infilt, drain):
    # set infiltration forcing
    ribasim_infiltration[0] = inl/day2sec # 0.0002007040335308
    # set drainage forcing
    ribasim_drainage[0] = drn/day2sec # 0.0002007040335308
    current_time+=1
    # run ribasim timestep
    ribasim_infiltration_integrated_old = ribasim_infiltration_integrated[0]
    ribasim_drainage_integrated_old = ribasim_drainage_integrated[0]
    riba.update_until(day2sec * current_time)
    # get integrated infiltration and drainage
#   print (ribasim_infiltration_integrated[0], ribasim_drainage_integrated[0])
#   print ('-----> ',ribasim_infiltration_integrated[0]-ribasim_infiltration_integrated_old, ribasim_infiltration[0]*day2sec)
    print ('-----> ',ribasim_drainage_integrated[0]-ribasim_drainage_integrated_old, ribasim_drainage[0]*day2sec)
    calculated.append(ribasim_infiltration_integrated[0]-ribasim_infiltration_integrated_old)
    expected.append(ribasim_infiltration[0]*day2sec)

# plt.plot(np.arange(len(calculated)),np.array(calculated),'r-',np.arange(len(expected)),np.array(expected),'b-')
plt.plot(np.arange(len(calculated)),np.array(calculated)-np.array(expected),'r-')
plt.show()
