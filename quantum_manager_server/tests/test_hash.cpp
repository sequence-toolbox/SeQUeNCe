//
// Created by Alex Kolar on 5/27/21.
//
#include <set>
#include <random>
#include "../src/qpp/qpp.h"

#include "../src/utils.hpp"

#define MAX_QUBIT_SIZE 4
#define TEST_SIZE 10000

int main()
{
    default_random_engine generator;
    uniform_int_distribution<u_int> distribution(1, MAX_QUBIT_SIZE);
    u_int num_qubits;
    u_int num_amplitudes;

    vector<u_int> indices;
    Eigen::VectorXcd state;
    key_type key;

    set<u_int> hash_set;

    for (int i = 0; i < TEST_SIZE; i++) {
        num_qubits = distribution(generator);
        num_amplitudes = 1 << num_qubits;
        uniform_int_distribution<u_int> index_distribution(1, num_qubits);

        indices = {index_distribution(generator)};
        state = Eigen::VectorXcd::Random(num_amplitudes);
        key = make_tuple(state, indices);

        hash_set.insert(hash<key_type>()(key));
    }

    cout << "Number of keys tested: " << TEST_SIZE << endl;
    cout << "Size of hash set: " << hash_set.size() << endl;
    cout << "Number of hash collisions: " << (TEST_SIZE - hash_set.size()) << endl;
}
