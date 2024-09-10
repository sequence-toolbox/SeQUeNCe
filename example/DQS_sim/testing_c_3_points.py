import glob
import os
import json
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
from qutip import qload
from qutip_integration import calc_scalar_c, calculate_fidelity


DATA_DIR = "/Users/alexkolar/Desktop/Lab/dqs_sim/3_points/results/1000_trials"

# plotting params
mpl.rcParams.update({'font.sans-serif': 'Helvetica',
                     'font.size': 12})
cmap = mpl.colormaps.get_cmap('hsv')
norm = mpl.colors.Normalize(vmin=-np.pi, vmax=np.pi)


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
good_GHZ = []
bad_GHZ = []
for file in results_files:
    dir_name = os.path.split(file)[0]

    with open(os.path.join(DATA_DIR, file)) as f:
        result_data = json.load(f)
    coherence = result_data["network config"]["templates"]["DQS_template"]["MemoryArray"]["coherence_time"]
    coherences.append(coherence)

    qobjs = []
    bell_states_init = []
    for trial in result_data["results"]:
        if trial["GHZ state"] is not None:
            file_path = os.path.join(DATA_DIR, dir_name, trial["GHZ state"])
            qobj = qload(file_path)
            qobjs.append(qobj)

            bell_states_init.append(trial["initial entangled states"])

    # calculate c
    avg_ghz = sum(qobjs) / len(qobjs)
    c = calc_scalar_c(avg_ghz)
    c_vals.append(abs(c))  # c is complex

    # calculate completion
    # num_trials = result_data["simulation config"]["num_trials"]
    num_successful_trials = len(result_data["results"])
    print(num_successful_trials)
    num_completed = result_data["results distribution"]["GHZ generated"]
    complete_percent.append(num_completed / num_successful_trials)

    # calculate fidelities
    fids = np.array([calculate_fidelity(qobj) for qobj in qobjs])

    print("Fidelity statistics:")
    print(f"\tMean: {np.mean(fids)}")
    print(f"\tMin: {np.min(fids)}")
    print(f"\tMax: {np.max(fids)}")
    # plt.hist(fids)
    # plt.show()

    # save example of good and bad GHZ state
    first_good_idx = np.where(fids > 0.5)[0][0]
    first_bad_idx = np.where(fids < 0.5)[0][0]
    good_GHZ.append(qobjs[first_good_idx])
    bad_GHZ.append(qobjs[first_bad_idx])

    # determine bell states for good and bad GHZ state
    good_bell_states = bell_states_init[first_good_idx]
    bad_bell_states = bell_states_init[first_bad_idx]
    print("Good initial bell states:")
    print(good_bell_states)
    print("Bad initial bell states:")
    print(bad_bell_states)


for i, (good_state, bad_state) in enumerate(zip(good_GHZ, bad_GHZ)):
    coherence = coherences[i]
    data_good = good_state.data.toarray()
    data_bad = bad_state.data.toarray()

    mag_good = np.abs(data_good)
    phase_good = np.angle(data_good)
    mag_bad = np.abs(data_bad)
    phase_bad = np.angle(data_bad)
    bottom = np.zeros_like(mag_good)

    # plotting
    _x = np.arange(8)
    _y = np.arange(8)
    _xx, _yy = np.meshgrid(_x, _y)
    x, y = _xx.ravel(), _yy.ravel()

    color_good = [cmap(norm(phase)) for phase in phase_good.ravel()]
    color_bad = [cmap(norm(phase)) for phase in phase_bad.ravel()]

    fig = plt.figure(figsize=(12, 6))
    ax1 = fig.add_subplot(121, projection='3d')
    ax2 = fig.add_subplot(122, projection='3d')

    ax1.bar3d(x, y,
              bottom.ravel(),
              1, 1,
              mag_good.ravel(),
              color=color_good, edgecolor='black')
    ax2.bar3d(x, y,
              bottom.ravel(),
              1, 1,
              mag_bad.ravel(),
              color=color_bad, edgecolor='black')

    plt.show()
