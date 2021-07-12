//
// Created by Alex Kolar on 4/14/21.
//
#include <iostream>
#include "../src/circuit.hpp"
#include "../src/quantum_manager.hpp"

int main()
{
    using namespace qpp;

    json input = json();
    std::vector<u_int> indices = {0};
    input["size"] = 1;
    input["gates"] = {{{"name", "h"}, {"indices", indices}}};
    Circuit* c = new Circuit(input);

    cout << "input json: " << input << endl;

    // create test manager
    vector<string> keys = {"1"};
    vector<double> amplitudes = {1, 0, 0, 0};
    QuantumManager qm = QuantumManager();
    qm.set(keys, amplitudes);

    cout << "input state:" << endl;
    cout << disp(qm.get("1")->state) << endl;

    // run circuit and observe
    qm.run_circuit(c, keys, 0);
    auto new_state = qm.get("1");

    cout << "new state:" << endl;
    cout << disp(new_state->state) << endl;

    // create new test state of 2 states
    json input_2 = json();
    indices = {0};
    input_2["size"] = 2;
    input_2["gates"] = {{{"name", "h"}, {"indices", indices}}};
    Circuit* c2 = new Circuit(input_2);

    keys = {"2", "3"};
    qm.set({"2"}, amplitudes);
    qm.set({"3"}, amplitudes);

    cout << "\ninput state 1:" << endl;
    cout << disp(qm.get("2")->state) << endl;
    cout << "input state 2:" << endl;
    cout << disp(qm.get("3")->state) << endl;

    qm.run_circuit(c2, keys, 0);
    new_state = qm.get("2");

    cout << "new state:" << endl;
    cout << disp(new_state->state) << endl;
    cout << "new keys:" << endl;
    auto new_keys = new_state->keys;
    for (auto key: new_keys) {
        cout << key << endl;
    }

    // apply to 2 states in wrong order
    qm.run_circuit(c2, {"3", "2"}, 0);
    new_state = qm.get("2");

    cout << "\nnew state:" << endl;
    cout << disp(new_state->state) << endl;
    cout << "new keys:" << endl;
    new_keys = new_state->keys;
    for (auto key: new_keys) {
        cout << key << endl;
    }

    // measurement of 2 states
    json input_3 = json();
    input_3["size"] = 2;
    input_3["measured_qubits"] = {0, 1};
    Circuit* c3 = new Circuit(input_3);

    keys = {"2", "3"};

    auto measured = qm.run_circuit(c3, keys, 0);

    cout << "\nMeasurement:" << endl;
    cout << "Key 2: " << measured["2"] << " state:" << endl;
    cout << disp(qm.get("2")->state) << endl;
    cout << "Key 3: " << measured["3"] << " state:" << endl;
    cout << disp(qm.get("3")->state) << endl;

    // measurement of 1 state in 2-qubit system
    json input_4 = json();
    input_4["size"] = 1;
    input_4["measured_qubits"] = {0};
    Circuit* c4 = new Circuit(input_4);

    keys = {"4", "5"};
    amplitudes = {0, 0, 0, 0, 1, 0, 0, 0};
    qm.set(keys, amplitudes);

    measured = qm.run_circuit(c4, {"4"}, 0);
    cout << "\nMeasurement:" << endl;
    cout << "Key 4: " << measured["4"] << " state:" << endl;
    cout << disp(qm.get("4")->state) << endl;
    cout << "Key 5 (not measured directly):" << endl;
    cout << disp(qm.get("5")->state) << endl;
}