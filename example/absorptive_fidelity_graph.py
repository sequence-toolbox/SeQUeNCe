from json5 import load
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable


filename = "results/absorptive_fidelity.json"
data = load(open(filename))
fidelity_mat = np.asarray(data["fidelity matrix"])

dim = 10
mean_num1_list = np.linspace(0.02, 0.1, num=dim, endpoint=True)
mean_num2_list = np.linspace(0.02, 0.1, num=dim, endpoint=True)
num1, num2 = np.meshgrid(mean_num1_list, mean_num2_list)

# plot the 2-d matrix
plt.rc('font', size=10)
plt.rc('axes', titlesize=18)
plt.rc('axes', labelsize=15)
plt.rc('xtick', labelsize=15)
plt.rc('ytick', labelsize=15)
plt.rc('legend', fontsize=15)

plt.rcParams['axes.titley'] = 1.05
plt.rcParams['axes.titlepad'] = 0

fig = plt.figure(figsize=(8, 6))
ax = fig.subplots()
divider = make_axes_locatable(ax)
cax = divider.append_axes('right', size='5%', pad=0.1)

im = ax.imshow(fidelity_mat, cmap=plt.cm.RdBu, extent=(0.02, 0.1, 0.1, 0.02))
fig.colorbar(im, cax=cax, orientation='vertical')
ax.invert_yaxis()
ax.set_title("Effective Fidelity versus Mean Photon Number")
ax.set_xlabel(r'Mean Photon Number of Source 1 $\mu_1$')
ax.set_ylabel(r'Mean Photon Number of Source 2 $\mu_2$')
ax.yaxis.set_ticks(np.linspace(0.02, 0.1, 5))
fig.tight_layout()
plt.savefig('fidelity.png')
plt.show()
