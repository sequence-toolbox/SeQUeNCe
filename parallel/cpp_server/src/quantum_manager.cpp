//
//  quantum_manager.cpp
//  server
//
//  Created by XIAOLIANG WU on 4/12/21.
//

#include <iostream>
#include <map>
#include <vector>
#include <memory>
#include "qpp/qpp.h"

#include "quantum_manager.hpp"
#include "circuit.hpp"
#include "utils.hpp"

#define CACHE_SIZE 1024

using namespace qpp;

// global caches
LRUCache<key_type, measure_value_type> measure_cache =
        LRUCache<key_type, measure_value_type>(CACHE_SIZE);
LRUCache<key_type, apply_value_type> h_cache =
        LRUCache<key_type, apply_value_type>(CACHE_SIZE);
LRUCache<key_type, apply_value_type> x_cache =
        LRUCache<key_type, apply_value_type>(CACHE_SIZE);
LRUCache<key_type, apply_value_type> y_cache =
        LRUCache<key_type, apply_value_type>(CACHE_SIZE);
LRUCache<key_type, apply_value_type> z_cache =
        LRUCache<key_type, apply_value_type>(CACHE_SIZE);
LRUCache<key_type, apply_value_type> ctrlx_cache =
        LRUCache<key_type, apply_value_type>(CACHE_SIZE);
LRUCache<key_type, apply_value_type> swap_cache =
        LRUCache<key_type, apply_value_type>(CACHE_SIZE);


Eigen::VectorXcd apply_wrapper(const Eigen::VectorXcd& state, const string& gate, vector<u_int> indices)
{
    Eigen::VectorXcd output_state(state.rows());
    key_type key = make_tuple(state, indices);

    if (gate == "h")
    {
        unique_lock<mutex> lock(h_cache.cache_mutex);

        if (h_cache.allocated(key)) {
            while (!h_cache.contains(key))
                h_cache.cache_cv.wait(lock);
            output_state = h_cache.get(key);
            lock.unlock();

        } else {
            h_cache.allocate(key);
            lock.unlock();
            output_state = apply(state, gt.H, {indices[0]});
            lock.lock();
            h_cache.put(key, output_state);
            h_cache.cache_cv.notify_all();
            lock.unlock();
        }
    }
    else if (gate == "x")
    {
        unique_lock<mutex> lock(x_cache.cache_mutex);

        if (x_cache.allocated(key)) {
            while (!x_cache.contains(key))
                x_cache.cache_cv.wait(lock);
            output_state = x_cache.get(key);
            lock.unlock();

        } else {
            x_cache.allocate(key);
            lock.unlock();
            output_state = apply(state, gt.X, {indices[0]});
            lock.lock();
            x_cache.put(key, output_state);
            x_cache.cache_cv.notify_all();
            lock.unlock();
        }
    }
    else if (gate == "y")
    {
        unique_lock<mutex> lock(y_cache.cache_mutex);

        if (y_cache.allocated(key)) {
            while (!y_cache.contains(key))
                y_cache.cache_cv.wait(lock);
            output_state = y_cache.get(key);
            lock.unlock();

        } else {
            y_cache.allocate(key);
            lock.unlock();
            output_state = apply(state, gt.Y, {indices[0]});
            lock.lock();
            y_cache.put(key, output_state);
            y_cache.cache_cv.notify_all();
            lock.unlock();
        }
    }
    else if (gate == "z")
    {
        unique_lock<mutex> lock(z_cache.cache_mutex);

        if (z_cache.allocated(key)) {
            while (!z_cache.contains(key))
                z_cache.cache_cv.wait(lock);
            output_state = z_cache.get(key);
            lock.unlock();

        } else {
            z_cache.allocate(key);
            lock.unlock();
            output_state = apply(state, gt.Z, {indices[0]});
            lock.lock();
            z_cache.put(key, output_state);
            z_cache.cache_cv.notify_all();
            lock.unlock();
        }
    }
    else if (gate == "cx")
    {
        unique_lock<mutex> lock(ctrlx_cache.cache_mutex);

        if (ctrlx_cache.allocated(key)) {
            while (!ctrlx_cache.contains(key))
                ctrlx_cache.cache_cv.wait(lock);
            output_state = ctrlx_cache.get(key);
            lock.unlock();

        } else {
            ctrlx_cache.allocate(key);
            lock.unlock();
            output_state = applyCTRL(state, gt.X, {indices[0]}, {indices[1]});
            lock.lock();
            ctrlx_cache.put(key, output_state);
            ctrlx_cache.cache_cv.notify_all();
            lock.unlock();
        }
    }
    else if (gate == "swap")
    {
        unique_lock<mutex> lock(swap_cache.cache_mutex);

        if (swap_cache.allocated(key)) {
            while (!swap_cache.contains(key))
                swap_cache.cache_cv.wait(lock);
            output_state = swap_cache.get(key);
            lock.unlock();

        } else {
            swap_cache.allocate(key);
            lock.unlock();
            output_state = apply(state, gt.SWAP, {indices[0], indices[1]});
            lock.lock();
            swap_cache.put(key, output_state);
            swap_cache.cache_cv.notify_all();
            lock.unlock();
        }
    }
    else {
        throw std::invalid_argument("undefined gate " + gate);
    }

    return output_state;
}

Eigen::VectorXcd vector_kron(Eigen::VectorXcd* first, Eigen::VectorXcd* second)
{
    long first_size = first->rows();
    long second_size = second->rows();
    long size = first_size * second_size;
    Eigen::VectorXcd out(size);

    for (int i = 0; i < size; i++)
        out(i) = (*first)(i / second_size) * (*second)(i % second_size);

    return out;
}


map<string, int> QuantumManager::run_circuit(Circuit* circuit, vector<string> keys, float meas_samp)
{
    // prepare circuit
    auto prepared = prepare_state(&keys);
    auto state = prepared.first;
    auto all_keys = prepared.second;

    // run circuit
    for (const auto& i: circuit->get_gates()) {
        string gate = i.first;
        vector<u_int> indices = i.second;
        state = apply_wrapper(state, gate, indices);
    }

    // perform measurement
    auto meas_indices = circuit->get_measured();
    if (meas_indices.empty()) {
        set(all_keys, state);
        return map<string, int>();
    }
    return measure_helper(state, meas_indices, all_keys, meas_samp);
}

std::pair<Eigen::VectorXcd, std::vector<string>> QuantumManager::prepare_state(std::vector<string>* keys)
{
    vector<Eigen::VectorXcd> old_states;
    vector<string> all_keys;

    // get all required states
    for (const string& key: *keys)
    {
        if (find(all_keys.begin(), all_keys.end(), key) == all_keys.end())
        {
            auto state = get(key);
            old_states.push_back(state->state);
            all_keys.insert(all_keys.end(), state->keys.begin(), state->keys.end());
        }
    }

    // compound states
    Eigen::VectorXcd new_state(1);
    new_state(0) = complex<double>(1, 0);
    for (auto state: old_states)
        new_state = vector_kron(&new_state, &state);

    // swap qubits if necessary
    string proper_key;
    u_int j;
    auto it = all_keys.begin();
    for (u_int i = 0; i < keys->size(); i++)
    {
        if (all_keys[i] != (*keys)[i])
        {
            proper_key = (*keys)[i];
            it = std::find(all_keys.begin(), all_keys.end(), proper_key);
            j = it - all_keys.begin(); // should always find proper_key in all_keys

            // perform swapping operation on state
            new_state = apply(new_state, gt.SWAP, {i, j});

            // swap keys
            all_keys[j] = all_keys[i];
            all_keys[i] = proper_key;
        }
    }

    pair<Eigen::VectorXcd, vector<string>> res = {new_state, all_keys};
    return res;
}

map<string, int> QuantumManager::measure_helper(const Eigen::VectorXcd& state,
                                                vector<u_int> indices,
                                                vector<string> all_keys,
                                                float samp) {
    auto num_qubits_meas = indices.size();
    vector<double> probs;
    vector<cmat> resultant_states;

    // check cache for result
    key_type key = make_tuple(state, indices);
    unique_lock<mutex> lock(measure_cache.cache_mutex);

    if (measure_cache.allocated(key))
    {
        // wait for value to be assigned if it isn't already
        while (!measure_cache.contains(key))
            measure_cache.cache_cv.wait(lock);
        measure_value_type value = measure_cache.get(key);
        lock.unlock();

        probs = std::get<0>(value);
        resultant_states = std::get<1>(value);
    }
    else
    {
        // allocate space in cache
        measure_cache.allocate(key);
        lock.unlock();

        // convert input indices to idx
        vector<idx> indices_idx(num_qubits_meas);
        for (int i = 0; i < num_qubits_meas; i++)
            indices_idx[i] = (idx) indices[i];

        // obtain measurement data using qpp
        auto meas_data = measure(state, gt.Id(1 << num_qubits_meas), indices_idx);
        probs = std::get<PROB>(meas_data);
        resultant_states = std::get<ST>(meas_data);

        // store in cache
        measure_value_type value = make_pair(probs, resultant_states);
        lock.lock();
        measure_cache.put(key, value);
        measure_cache.cache_cv.notify_all();
        lock.unlock();
    }

    // determine measurement result using random sample
    double cum_sum = 0;
    int res = 0;
    while (res < probs.size())
    {
        cum_sum += probs[res];
        if (samp < cum_sum)
            break;
        res++;
    }

    // values for assigning new states
    map<string, int> output;
    u_int index;
    int res_bit;
    Eigen::VectorXcd state0(2);
    state0(0) = complex<double>(1,0);
    state0(1) = complex<double>(0,0);
    Eigen::VectorXcd state1(2);
    state1(0) = complex<double>(0,0);
    state1(1) = complex<double>(1,0);
    vector<Eigen::VectorXcd> output_states = {state0, state1};

    // assign state for measured qubits
    for (int i = 0; i < num_qubits_meas; i++)
    {
        index = indices[i];
        res_bit = (res >> (num_qubits_meas-1-i)) & 1;
        set({all_keys[index]}, output_states[res_bit]);
        output[all_keys[index]] = res_bit;
    }

    // assign state for non-measured qubits
    vector<string> no_measure_keys;
    int cur_index = 0;
    for (auto end: indices) {
        while (cur_index < end) {
            no_measure_keys.push_back(all_keys[cur_index]);
            cur_index++;
        }
        cur_index = end + 1;
    }

    if (!no_measure_keys.empty())
        set(no_measure_keys, resultant_states[res]);

    return output;
}
