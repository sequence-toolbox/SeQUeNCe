//
//  circuit.hpp
//  server
//
//  Created by XIAOLIANG WU on 4/12/21.
//

#ifndef circuit_hpp
#define circuit_hpp

#include <stdio.h>
#include <vector>
#include <string>
#include <complex>
#include "nlohmann/json.hpp"
#include "qpp/qpp.h"
#include <Eigen/Dense>

using json = nlohmann::json;

class Circuit {
public:
    u_int size;
    std::vector<std::pair<std::string, std::vector<u_int>>> gates;
    std::vector<u_int> measured_qubits;

    explicit Circuit(json);
    std::vector<std::pair<std::string, std::vector<u_int>>> get_gates()
    {
        return gates;
    };
    std::vector<u_int> get_measured()
    {
        return measured_qubits;
    };
};

#endif /* circuit_hpp */
