//
// Created by Alex Kolar on 7/7/21.
//

#include <iostream>
#include <vector>
#include <pthread.h>
#include <Eigen/Core>
#include "../src/nlohmann/json.hpp"

#include "../src/quantum_manager.hpp"

#define NO_THREADS 5
#define QUBITS_PER_THREAD 100

void* task(void*);
struct task_args {
    int key_start;
};

QuantumManager qm;

int main()
{
    Eigen::initParallel();
    pthread_t threadA[NO_THREADS];

    for (int i = 0; i < NO_THREADS; i++) {
        auto args = (struct task_args *) malloc(sizeof(struct task_args));
        args->key_start = i * QUBITS_PER_THREAD;
        pthread_create(&threadA[i], NULL, task, (void *)args);
    }

    for (auto & i : threadA) {
        pthread_join(i, NULL);
    }

    return 0;
}

void* task(void* args)
{
    int key_start = ((struct task_args*) args)->key_start;

    json circ_json_h = {
            {"size", 1},
            {"gates", { { {"name", "h"},
                          {"indices", {0}} } } },
            {"measured_qubits", {0}}
    };

    json circ_json_x = {
            {"size", 1},
            {"gates", { { {"name", "x"},
                                {"indices", {0}} } } },
            {"measured_qubits", {0}}
    };

    for (int key = key_start; key < key_start + QUBITS_PER_THREAD; key++)
    {
        vector<string> ks = {to_string(key)};
        vector<double> amplitudes = {1.0, 0.0, 0.0, 0.0};
        qm.set(ks, amplitudes);

        Circuit* circuit;
        if (key % 2)
            circuit = new Circuit(circ_json_h);
        else
            circuit = new Circuit(circ_json_x);

        float meas_samp = 0;
        map<string, int> res = qm.run_circuit(circuit, ks, meas_samp);
    }

    return nullptr;
}
