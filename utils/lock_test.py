import multiprocessing
from itertools import product


NUM_PROCS = 5

def test_func(num, lock):
    print(lock)
    if num >= NUM_PROCS / 2:
        lock.acquire()

manager = multiprocessing.Manager()
lock = manager.Lock()
nums = list(range(NUM_PROCS))

p = multiprocessing.Pool(NUM_PROCS)
p.starmap(test_func, product(nums, [lock]))
p.close()
p.terminate()

