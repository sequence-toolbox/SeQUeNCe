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
c_color = 'cornflowerblue'
percent_color = 'coral'


results_files = glob.glob("(*km)*/main.json", root_dir=DATA_DIR)

# get all GHZ statistics
distances = []
c_vals = []
complete_percent = []
for file in results_files:
    dir_name = os.path.split(file)[0]

    with open(os.path.join(DATA_DIR, file)) as f:
        result_data = json.load(f)
    distance = result_data["network config"]["qconnections"][0]["distance"]
    distance /= 1e3  # convert to km
    distances.append(distance)

    qobjs = []
    for trial in result_data["results"]:
        if trial["GHZ state"] is not None:
            file_path = os.path.join(DATA_DIR, dir_name, trial["GHZ state"])
            qobj = qload(file_path)
            qobjs.append(qobj)

    # calculate c
    avg_ghz = sum(qobjs) / len(qobjs)
    c = calc_scalar_c(avg_ghz)
    c_vals.append(abs(c))  # c is complex

    # calculate completion
    num_trials = result_data["simulation config"]["num_trials"]
    num_completed = result_data["results distribution"]["GHZ generated"]
    complete_percent.append(num_completed / num_trials)

# sort
distances, c_vals = zip(*sorted(zip(distances, c_vals)))


# plotting
fig, ax = plt.subplots()
ax2 = ax.twinx()
ax.plot(distances, c_vals,
        '-o', color=c_color)
ax2.plot(distances, complete_percent,
         '-o', color=percent_color)

ax.set_xlabel("Distance (km)")
ax.set_ylabel("C", color=c_color)
ax2.set_ylabel("Completion Rate", color=percent_color)
ax.set_ylim((-0.1, 1.1))
ax2.set_ylim((-0.1, 1.1))
ax.grid(True)

fig.tight_layout()
fig.show()
