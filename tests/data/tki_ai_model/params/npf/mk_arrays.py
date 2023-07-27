# %%
import numpy as np

# %%
nlay, nrow, ncol = 1, 11, 10
path = r"c:\src\imod_coupler\tests\data\tki_ai_model\params\npf"

# for first repeating period
kh1 = 10000.0
kh2 = 10.0
kv = 1.0
kh_array = np.full((nlay, nrow, ncol), kh1)
kh_array[0, 5:10, 5:9] = kh2
kv_array = np.full((nlay, nrow, ncol), kv)
kh_array.tofile(path + "\\kh_1", sep="")
np.savetxt(path + "\\kh_1.txt", kh_array[0, :, :])

kv_array.tofile(path + "\\kv_1", sep="")

# second repeating period
kh = 0.1
kh2 = 0.001
kv = 1.0
kh_array = np.full((nlay, nrow, ncol), kh)
kh_array[0, 5:10, 5:9] = kh2
kv_array = np.full((nlay, nrow, ncol), kv)
kh_array.tofile(path + "\\kh_2", sep="")
np.savetxt(path + "\\kh_2.txt", kh_array[0, :, :])
kv_array.tofile(path + "\\kv_2", sep="")
