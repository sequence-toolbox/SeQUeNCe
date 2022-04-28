from json5 import load
import numpy as np
import matplotlib.pyplot as plt


filename = "results/absorptive.json"
data = load(open(filename))

direct_results = data["direct results"]
bs_results = data["bs results"]
print(len(bs_results))
print(len(bs_results[1]))

# plotting direct detection results
bins = np.zeros(4)
for trial in direct_results:
    bins += np.array(trial["counts"])
norm = (1 / sum(bins))
bins *= norm

plt.bar(np.arange(4), bins)
plt.show()

# # plotting bs results
# freq_0 = []
# freq_1 = []
# for res in bs_results:
#     counts = np.zeros(2)
#     total = 0
#     for trial in res:
#         counts += np.array(trial["counts"])
#         total += trial["total_count"]
#     counts *= (1 / total)
#     freq_0.append(counts[0])
#     freq_1.append(counts[1])
#
# plt.plot(freq_0)
# plt.plot(freq_1)
# plt.show()
