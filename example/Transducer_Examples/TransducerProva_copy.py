import random
import matplotlib.pyplot as plt

NUM_TRIALS = 100  # Aumentato il numero di trials per vedere la convergenza
EFFICIENCY = 0.5

detector1_percentages = []
detector2_percentages = []

for num_trials in range(1, NUM_TRIALS + 1):
    total_photons = 0
    detector1_photons = 0
    detector2_photons = 0

    for trial in range(num_trials):
        if random.random() < EFFICIENCY:
            detector1_photons += 1
        else:
            detector2_photons += 1

    total_photons = detector1_photons + detector2_photons
    percent_detector1 = (detector1_photons / total_photons) * 100
    percent_detector2 = (detector2_photons / total_photons) * 100

    detector1_percentages.append(percent_detector1)
    detector2_percentages.append(percent_detector2)

# Plot delle percentuali di rilevamento
plt.figure(figsize=(10, 6))

plt.plot(range(1, NUM_TRIALS + 1), detector1_percentages, label='Microwave Detector Percentage')
plt.plot(range(1, NUM_TRIALS + 1), detector2_percentages, label='Optical Detector Percentage')

plt.axhline(y=50, color='r', linestyle='--', label='Ideal 50%')

plt.title('Percentage of Photons Detected by Detectors')
plt.xlabel('Number of Trials')
plt.ylabel('Percentage (%)')
plt.xticks(range(1, NUM_TRIALS + 1, 5))
plt.yticks(range(0, 101, 10))
plt.legend()
plt.grid(True)
plt.tight_layout()

plt.show()
