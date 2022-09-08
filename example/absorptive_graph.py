from json5 import load
import matplotlib.pyplot as plt


filename = "results/absorptive.json"
data = load(open(filename))

direct_results = data["direct results"]
bs_results = data["bs results"]

# plotting bs results
freq_0 = [res[0] for res in bs_results]
freq_1 = [res[1] for res in bs_results]
plt.plot(freq_0)
plt.plot(freq_1)
plt.show()
