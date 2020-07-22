import numpy as np


def read_mapping(map_file: str):
    map_arr = np.loadtxt(map_file, dtype=np.int32)
    # 1-based indices (fortran) to 0-based indices (python)
    map_arr[:, 0] = map_arr[:, 0] - 1
    map_arr[:, 1] = map_arr[:, 1] - 1

    map_in = {}
    for gw, sv in zip(map_arr[:, 0], map_arr[:, 1]):
        map_in.setdefault(gw, []).append(sv)

    return map_in


def invert_mapping(map_in: dict):
    map_out = {}
    for i, lst in map_in.items():
        for j in lst:
            if j not in map_out:
                map_out[j] = []
            map_out[j].append(i)
    for key in map_out.keys():
        map_out[key] = list(set(map_out[key]))
    return map_out
