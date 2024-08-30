import glob
import os
import json
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from qutip import qload
from qutip_integration import calc_scalar_c, calculate_fidelity


DATA_DIR = "/Users/alexkolar/Desktop/Lab/dqs_sim/3_points/results/1000_trials"

# plotting params
mpl.rcParams.update({'font.sans-serif': 'Helvetica',
                     'font.size': 12})
tick_fmt = '%.0f%%'
c_color = 'cornflowerblue'
percent_color = 'coral'
bar_width = 0.4


results_files = glob.glob("*/main.json", root_dir=DATA_DIR)

# get basic info
with open(os.path.join(DATA_DIR, results_files[0])) as f:
    results = json.load(f)
net_config = results['network config']
num_nodes = len(net_config['nodes'])

# get all GHZ statistics
coherences = []
c_vals = []
fid_vals = []
complete_percent = []
for file in results_files:
    dir_name = os.path.split(file)[0]

    with open(os.path.join(DATA_DIR, file)) as f:
        result_data = json.load(f)
    coherence = result_data["network config"]["templates"]["DQS_template"]["MemoryArray"]["coherence_time"]
    coherences.append(coherence)

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

    # # calculate fidelities
    # fids = [calculate_fidelity(qobj) for qobj in qobjs]
    # print(np.mean(fids), np.min(fids), np.max(fids))

    # calculate completion
    # num_trials = result_data["simulation config"]["num_trials"]
    num_successful_trials = len(result_data["results"])
    print(num_successful_trials)
    num_completed = result_data["results distribution"]["GHZ generated"]
    complete_percent.append(num_completed / num_successful_trials)

# sort
coherences, c_vals, complete_percent = zip(*sorted(zip(coherences, c_vals, complete_percent)))
complete_percent = np.array(complete_percent)

# calculate values
eta = num_nodes*(1 - np.array(c_vals).flatten())
eta_tilde = complete_percent * eta


# plotting
fig, ax = plt.subplots()
ax2 = ax.twinx()
x_points_eta = np.array(range(len(c_vals))) - bar_width/2
x_points_percent = np.array(range(len(c_vals))) + bar_width/2
ax.bar(x=x_points_eta, height=eta_tilde,
       color=c_color, edgecolor='k', width=bar_width, zorder=3)
ax2.bar(x=x_points_percent, height=100*complete_percent,
        color=percent_color, edgecolor='k', width=bar_width)
# ax.axhline(y=1,
#            ls='--', color='k')

ax.set_xlabel("Coherence time (s)")
ax.set_ylabel(r"$\tilde{\eta}$", color=c_color)
ax2.set_ylabel("Completion Rate", color=percent_color)
yticks = ticker.FormatStrFormatter(tick_fmt)
ax2.yaxis.set_major_formatter(yticks)
ax2.set_ylim((0, 100))
ax.grid(True, zorder=0)

fig.tight_layout()
fig.show()
