import sys
import os
import time
import statistics as stats

runtimes = []

def timeit_wrapper(func):
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        return_val = func(*args, **kwargs)
        end = time.perf_counter()
        runtimes.append(end - start)
        return return_val
    return wrapper


if __name__ == "__main__":
    '''
    Program for timing a script, returns average of several runs
    input: relative path to script
    '''

    script = sys.argv[1]
    try:
        num_trials = int(sys.argv[2])
    except IndexError:
        num_trials = 10

    @timeit_wrapper
    def run():
        os.system("python3 " + script)

    print("running timing test for {} with {} trials".format(script, num_trials))

    for i in range(num_trials):
        print("\trunning attempt number {} ... ".format(i + 1), end='', flush=True)
        run()
        print("ran in {}s".format(runtimes[-1]))

    print("mean time: {}".format(stats.mean(runtimes)))
    print("min time:  {}".format(min(runtimes)))
    print("max time:  {}".format(max(runtimes)))


