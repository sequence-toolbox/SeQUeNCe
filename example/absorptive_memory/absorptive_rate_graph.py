"""If you find the codes in this repository useful, please cite this work as follows:
--- A. Zang, A. Kolar, J. Chung, M. Suchara, T. Zhong and R. Kettimuthu, "Simulation of Entanglement Generation between Absorptive Quantum Memories," 2022 IEEE International Conference on Quantum Computing and Engineering (QCE), Broomfield, CO, USA, 2022, pp. 617-623, doi: 10.1109/QCE53715.2022.00084. 
"""

from json5 import load
import numpy as np
import matplotlib.pyplot as plt


filename = "results/absorptive_rate.json"
data = load(open(filename))

list1, list2, list3, list4 = data["rate_list"]
mode_num_list = np.arange(10, 105, step=5)

plt.rc('font', size=10)
plt.rc('axes', titlesize=18)
plt.rc('axes', labelsize=15)
plt.rc('xtick', labelsize=15)
plt.rc('ytick', labelsize=15)
plt.rc('legend', fontsize=15)

fig = plt.figure(figsize=(8, 5))
ax = fig.subplots()

ax.plot(mode_num_list, list1, label=r'$\mu=0.02$')
ax.plot(mode_num_list, list2, label=r'$\mu=0.03$')
ax.plot(mode_num_list, list3, label=r'$\mu=0.04$')
ax.plot(mode_num_list, list4, label=r'$\mu=0.05$')

ax.set_title("Entanglement Generation Rate with Mode Number")
ax.set_xlabel("Mode Number $M$")
ax.set_ylabel("Entanglement Generation Rate $R$ (Hz)")
ax.legend()
fig.tight_layout()
plt.savefig('rate.png')
plt.show()
plt.show()
