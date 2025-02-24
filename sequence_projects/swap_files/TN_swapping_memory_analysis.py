from swap_TN_direct import *
import json
import tracemalloc
import gc


# params
mean_photon_num = 0.1
num_modes = 8
efficiency = 0.9
truncations = [1,2,3,4,5,6]
# truncations = [1,2,3]
error_tolerances = [1e-4, 1e-5, 1e-6, 1e-7, 1e-8, 1e-9, 1e-10]
TN_data = []
sparse_data = []

num_iter = 1

# tracemalloc.start()
for error_tolerance in error_tolerances:
    TN_data_error_tol = []
    for trunc in truncations:
        N = trunc+1
        
        time_taken = 0

        psi = new_ls(N, mean_photon_num, error_tolerance) 
        # TN data:
        # start = time.time()
        net_size_diff = 0
        for _ in range(num_iter):
            gc.collect()
            tracemalloc.start()
            # start_snapshot = tracemalloc.take_snapshot()


            psi = extend_MPS(psi)
            psi = bell_state_measurement(psi, N, psi.site_tags, num_modes, efficiency, error_tolerance, pnr = False, compress=True, contract=True)
            
            idler_angles = np.array([0])
            signal_angles = np.linspace(0, np.pi, 15)

            coincidence = rotate_and_measure(psi, N, psi.site_tags, num_modes, efficiency, error_tolerance, idler_angles, signal_angles, pnr = False, compress=True, contract=True, draw = False)
            
            # end_snapshot = tracemalloc.take_snapshot()
            # time_taken += time.time() - start
            current, peak =  tracemalloc.get_traced_memory()
            # memory_diff = end_snapshot.compare_to(start_snapshot, key_type = "filename")

            # for i in memory_diff:
            #     net_size_diff += i.size_diff
            net_size_diff += peak    

            tracemalloc.stop()
            tracemalloc.clear_traces()    
        
        TN_data_error_tol.append(net_size_diff/num_iter)
                
        print("truncation:", trunc)
    print("error:", error_tolerance)
    TN_data.append(TN_data_error_tol)
tracemalloc.stop()


timing_data = {error_tol:TN for error_tol, TN in zip(error_tolerances, TN_data)}
print(timing_data)

json.dump(timing_data, open(f"memory_data_mpn{int(mean_photon_num*100)}.json", "w"))





# params
mean_photon_num = 0.5
num_modes = 8
efficiency = 0.9
truncations = [1,2,3,4,5,6]
# truncations = [1,2,3]
error_tolerances = [1e-4, 1e-5, 1e-6, 1e-7, 1e-8, 1e-9, 1e-10]
TN_data = []
sparse_data = []

num_iter = 1

# tracemalloc.start()
for error_tolerance in error_tolerances:
    TN_data_error_tol = []
    for trunc in truncations:
        N = trunc+1
        
        time_taken = 0

        psi = new_ls(N, mean_photon_num, error_tolerance) 
        # TN data:
        # start = time.time()
        net_size_diff = 0
        for _ in range(num_iter):
            gc.collect()
            tracemalloc.start()
            # start_snapshot = tracemalloc.take_snapshot()


            psi = extend_MPS(psi)
            psi = bell_state_measurement(psi, N, psi.site_tags, num_modes, efficiency, error_tolerance, pnr = False, compress=True, contract=True)
            
            idler_angles = np.array([0])
            signal_angles = np.linspace(0, np.pi, 15)

            coincidence = rotate_and_measure(psi, N, psi.site_tags, num_modes, efficiency, error_tolerance, idler_angles, signal_angles, pnr = False, compress=True, contract=True, draw = False)
            
            # end_snapshot = tracemalloc.take_snapshot()
            # time_taken += time.time() - start
            current, peak =  tracemalloc.get_traced_memory()
            # memory_diff = end_snapshot.compare_to(start_snapshot, key_type = "filename")

            # for i in memory_diff:
            #     net_size_diff += i.size_diff
            net_size_diff += peak    

            tracemalloc.stop()
            tracemalloc.clear_traces()    
        
        TN_data_error_tol.append(net_size_diff/num_iter)
                
        print("truncation:", trunc)
    print("error:", error_tolerance)
    TN_data.append(TN_data_error_tol)
tracemalloc.stop()


timing_data = {error_tol:TN for error_tol, TN in zip(error_tolerances, TN_data)}
print(timing_data)

json.dump(timing_data, open(f"memory_data_mpn{int(mean_photon_num*100)}.json", "w"))



