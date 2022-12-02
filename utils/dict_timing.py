import time
import multiprocessing
import numpy as np


NUM_KEYS = 10000

test_dict = {}
for i in range(NUM_KEYS):
    test_dict[i] = np.random.random()

mgr = multiprocessing.Manager()
mgr_dict = mgr.dict()
mgr_dict.update(test_dict)

start1 = time.time()
for i in range(NUM_KEYS):
    val = test_dict[i]
end1 = time.time()
print("Normal read:", end1 - start1)

start2 = time.time()
for i in range(NUM_KEYS):
    val = mgr_dict[i]
end2 = time.time()
print("Manager read:", end2 - start2)

print("Ratio:", (end2 - start2) / (end1 - start1))
