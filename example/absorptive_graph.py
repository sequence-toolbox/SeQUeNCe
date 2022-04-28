from json5 import load
import numpy as np
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
import matplotlib.ticker as tck
from matplotlib.colors import LightSource


filename = "results/absorptive.json"
data = load(open(filename))

direct_results = data["direct results"]
bs_results = data["bs results"]

# acquire direct detection results
bins = np.zeros(4)
for trial in direct_results:
    bins += np.array(trial["counts"])
norm = (1 / sum(bins))
bins *= norm

# acquire bs results
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

# curve fitting
def sin(x, A, phi, z): return A*np.sin(x + phi) + z
params_0, _ = curve_fit(sin, phases, freq_0)
params_1, _ = curve_fit(sin, phases, freq_1)

# off-diagonal density matrix
visibility = abs(params_0[0]) + abs(params_1[0])
off_diag = visibility * (bins[1] + bins[2]) / 2

# plotting density matrix
fig = plt.figure()
ax = fig.add_subplot(projection="3d")
ax.view_init(azim=-30)

width = depth = 0.8
x = np.array([0, 1, 2, 3, 1, 2]) - (width/2)
y = np.array([0, 1, 2, 3, 2, 1]) - (width/2)
color = (['tab:blue'] * 4) + (['tab:orange'] * 2)
ls = LightSource(100, 60)
ax.bar3d(x, y, np.zeros(6), width, depth, list(bins) + [off_diag, off_diag],
         color=color, edgecolor='black', shade=True, lightsource=ls)

ax.set_title(r'Reconstructed $|\tilde{\rho}|$')
ax.set_xticks([0, 1, 2, 3])
ax.set_yticks([0, 1, 2, 3])
ax.set_xticklabels([r'$|00\rangle$', r'$|01\rangle$', r'$|10\rangle$', r'$|11\rangle$'])
ax.set_yticklabels([r'$\langle00|$', r'$\langle01|$', r'$\langle10|$', r'$\langle11|$'])
plt.show()

# plotting interference
fig = plt.figure()
ax = fig.add_subplot()

ax.plot(phases/np.pi, freq_0, marker='o', ls='', label=r'$p_{01}$')
ax.plot(phases/np.pi, freq_1, marker='o', ls='', label=r'$p_{10}$')
plt.plot(phases/np.pi, sin(phases, *params_0), color='tab:blue', ls='--')
plt.plot(phases/np.pi, sin(phases, *params_1), color='tab:orange', ls='--')

ax.xaxis.set_major_formatter(tck.FormatStrFormatter(r'%g $\pi$'))
ax.xaxis.set_major_locator(tck.MultipleLocator(base=0.5))
ax.set_ylim([0, 1])
ax.set_xlabel("Relative phase")
ax.legend()
plt.show()

# output
print("Detector 1 visibility:", abs(params_0[0]) * 2)
print("Detector 2 visibility:", abs(params_1[0]) * 2)
print("Combined:", abs(params_0[0]) + abs(params_1[0]))
