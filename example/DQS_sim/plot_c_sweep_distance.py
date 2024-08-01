import glob
import os
import json
import matplotlib as mpl
import matplotlib.pyplot as plt
from qutip import qload
from qutip_integration import calc_scalar_c


DATA_DIR = "/Users/alexkolar/Desktop/Lab/dqs_sim/sweep_length/results"

# plotting params
mpl.rcParams.update({'font.sans-serif': 'Helvetica',
                     'font.size': 12})


# results_files = glob.glob("(*km)*/main.json", root_dir=DATA_DIR)
results_files = glob.glob("(*km)*/*.qu", root_dir=DATA_DIR)

# calculate average GHZ
qobj_by_distance = {}
for file in results_files:
    long_name = os.path.split(file)[0]

    # get distance
    distance_str = long_name[long_name.find("(") + 1:long_name.find(")")]
    distance_str = distance_str[:-2]  # remove 'km'
    distance = int(distance_str)

    file_to_load = os.path.splitext(file)[0]
    file_to_load = os.path.join(DATA_DIR, file_to_load)
    qobj = qload(file_to_load)
    if distance in qobj_by_distance:
        qobj_by_distance[distance].append(qobj)
    else:
        qobj_by_distance[distance] = [qobj]

# calculate c
c_by_distance = {}
for distance, qobjs in qobj_by_distance.items():
    avg_ghz = sum(qobjs) / len(qobjs)
    c = calc_scalar_c(avg_ghz)
    c_by_distance[distance] = abs(c)  # c is complex


# plotting
x_vals, y_vals = zip(*c_by_distance.items())
x_vals, y_vals = list(x_vals), list(y_vals)
x_vals, y_vals = zip(*sorted(zip(x_vals, y_vals)))

plt.plot(x_vals, y_vals,
         '-o', color='cornflowerblue')
plt.xlabel("Distance (km)")
plt.ylabel("C")
plt.ylim((-0.1, 1.1))

plt.tight_layout()
plt.show()
