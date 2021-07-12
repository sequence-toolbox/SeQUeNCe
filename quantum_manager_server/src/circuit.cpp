//
//  circuit.cpp
//  server
//
//  Created by XIAOLIANG WU on 4/12/21.
//

#include "circuit.hpp"
#include "nlohmann/json.hpp"
#include <vector>
#include "qpp/qpp.h"
#include <Eigen/Dense>
#include <iostream>

using json = nlohmann::json;

Circuit::Circuit(json s_json)
{
    size = s_json["size"];

    for (auto gate: s_json["gates"])
    {
        std::string name = gate["name"];
        std::vector<u_int> indices = gate["indices"];
        std::pair<std::string, std::vector<u_int>> element = {name, indices};
        gates.push_back(element);
    }
    
    for (const auto& m_q: s_json["measured_qubits"])
        measured_qubits.push_back(m_q);
}
