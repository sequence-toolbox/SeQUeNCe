from json5 import load
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as tck

filename = "results/absorptive.json"
data = load(open(filename))

direct_results = data["direct results"]
bs_results = data["bs results"]

# plotting direct detection results
fig = plt.figure()
ax = fig.add_subplot(projection="3d")
ax.view_init(azim=-30)

bins = np.zeros(4)
for trial in direct_results:
    bins += np.array(trial["counts"])
norm = (1 / sum(bins))
bins *= norm

width = depth = 0.9
bottom = np.zeros(4)
x = np.arange(4) - (width/2)
y = np.arange(4) - (width/2)
ax.bar3d(x, y, bottom, width, depth, bins, edgecolor='black', shade=False)
plt.show()

# plotting bs results
fig = plt.figure()
ax = fig.add_subplot()

num = data["num_phase"]
phases = np.linspace(0, 2*np.pi, num=num)
freq_0 = []
freq_1 = []
for res in bs_results:
    counts = np.zeros(2)
    total = 0
    for trial in res:
        counts += np.array(trial["counts1"])
        total += trial["total_count1"]
    counts *= (1 / total)
    freq_0.append(counts[0])
    freq_1.append(counts[1])

ax.plot(phases/np.pi, freq_0, marker='o', label=r'$p_{01}$')
ax.plot(phases/np.pi, freq_1, marker='o', label=r'$p_{10}$')
ax.xaxis.set_major_formatter(tck.FormatStrFormatter('%g $\pi$'))
ax.xaxis.set_major_locator(tck.MultipleLocator(base=1.0))
ax.set_ylim([0, 1])
ax.set_xlabel("Relative phase")
ax.legend()
plt.show()
