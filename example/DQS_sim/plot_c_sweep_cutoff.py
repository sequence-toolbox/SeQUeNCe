import glob
import os
import json
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from qutip import qload
from qutip_integration import calc_scalar_c, calculate_fidelity


DATA_DIR = "/Users/alexkolar/Desktop/Lab/dqs_sim/testing/sweep_cutoff_test_3/results"

# plotting params
mpl.rcParams.update({'font.sans-serif': 'Helvetica',
                     'font.size': 12})
tick_fmt = '%.0f%%'
c_color = 'cornflowerblue'
percent_color = 'coral'


results_files = glob.glob("*/main.json", root_dir=DATA_DIR)

# get basic info
with open(os.path.join(DATA_DIR, results_files[0])) as f:
    results = json.load(f)
net_config = results['network config']
num_nodes = len(net_config['nodes'])

# get all GHZ statistics
cutoffs = []
c_vals = []
fid_vals = []
complete_percent = []
for file in results_files:
    dir_name = os.path.split(file)[0]

    with open(os.path.join(DATA_DIR, file)) as f:
        result_data = json.load(f)
    cutoff_time = result_data["simulation config"]["cutoff_time"]
    cutoffs.append(cutoff_time)

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

    # calculate fidelities
    fids = [calculate_fidelity(qobj) for qobj in qobjs]
    print(np.mean(fids), np.min(fids), np.max(fids))

    # calculate completion
    num_trials = result_data["simulation config"]["num_trials"]
    num_completed = result_data["results distribution"]["GHZ generated"]
    complete_percent.append(num_completed / num_trials)

# sort
cutoffs, c_vals = zip(*sorted(zip(cutoffs, c_vals)))
complete_percent = np.array(complete_percent)


# plotting
fig, ax = plt.subplots()
ax2 = ax.twinx()
ax.plot(cutoffs, num_nodes*(1 - np.array(c_vals)),
        '-o', color=c_color)
ax2.plot(cutoffs, 100 * complete_percent,
         '-o', color=percent_color)

ax.set_xlabel("Cutoff time (s)")
ax.set_ylabel(r"$d(1 - C)$", color=c_color)
ax2.set_ylabel("Completion Rate", color=percent_color)
ax2.set_ylim((-10, 110))
yticks = ticker.FormatStrFormatter(tick_fmt)
ax2.yaxis.set_major_formatter(yticks)
ax.grid(True)

fig.tight_layout()
fig.show()
