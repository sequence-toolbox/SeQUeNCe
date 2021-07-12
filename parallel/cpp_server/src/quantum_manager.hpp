//
//  quantum_manager.hpp
//  server
//
//  Created by XIAOLIANG WU on 4/12/21.
//

#ifndef quantum_manager_hpp
#define quantum_manager_hpp

#include <stdio.h>
#include <vector>
#include <complex>
#include <map>
#include <shared_mutex>
#include <mutex>
#include <Eigen/Dense>
#include "qpp/qpp.h"

#include "circuit.hpp"
#include "utils.hpp"

using namespace std;

class State {
public:
    vector<string> keys;
    Eigen::VectorXcd state;

    string serialization()
    {
        json j;
        j["keys"] = keys;
        vector<double> complex_vect;
        complex<double> c;
        for (u_int i = 0; i<state.size(); ++i) {
            c = state(i);
            complex_vect.push_back(c.real());
            complex_vect.push_back(c.imag());
        }
        j["state"] = complex_vect;
        return j.dump();
    }
    State(Eigen::VectorXcd s, vector<string> k) {
        assert (!k.empty());
        state = s;
        keys = k;
    }
};

class QuantumManager {
public:
    map<string, State*> states;
    shared_mutex map_lock;

    State* get(const string& key)
    {
        shared_lock lock(map_lock);
        return states[key];
    }
    void set(const vector<string>& ks, const vector<double>& amplitudes)
    {
        unique_lock lock(map_lock);
        const unsigned long size = amplitudes.size() / 2;
        Eigen::VectorXcd complex_amp(size);

        for (int i=0; i < amplitudes.size(); i+=2) {
            complex<double> complex_num (amplitudes[i], amplitudes[i+1]);
            complex_amp(i / 2) = complex_num;
        }

        auto s = new State(complex_amp, ks);
        for (const string& k: ks){
            states[k] = s;
        }
    }
    void set(const vector<string>& ks, Eigen::VectorXcd amplitudes)
    {
        unique_lock lock(map_lock);
        auto s = new State(amplitudes, ks);
        for (const string& k: ks) {
            states[k] = s;
        }
    }
    bool exist(const string& key)
    {
        shared_lock lock(map_lock);
        return states.find(key) != states.end();
    }
    map<string, int> run_circuit(Circuit*, vector<string>, float);

private:
    pair<Eigen::VectorXcd, vector<string>> prepare_state(vector<string>*);
    map<string, int> measure_helper(const Eigen::VectorXcd&, vector<u_int>, vector<string>, float);
};

#endif /* quantum_manager_hpp */
