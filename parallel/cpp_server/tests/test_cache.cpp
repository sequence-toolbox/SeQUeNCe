//
// Created by Alex Kolar on 4/21/21.
//
#include <map>
#include <vector>
#include "../src/qpp/qpp.h"

#include "../src/utils.hpp"

int main()
{
    /// basic functionality

    LRUCache<int, double*> cache(3);

    auto* one_ptr = new double;
    *one_ptr = 1.0;
    auto* two_ptr = new double;
    *two_ptr = 2.0;
    auto* three_ptr = new double;
    *three_ptr = 3.0;
    auto* four_ptr = new double;
    *four_ptr = 4.0;

    cache.put(1, one_ptr);
    cache.put(2, two_ptr);

    cout << "Value in cache at 1: " << *cache.get(1) << endl;
    cout << "Value in cache at 2: " << *cache.get(2) << endl;
    if (!cache.contains(3))
        cout << "Nothing stored at 3 yet." << endl;

    cache.put(3, three_ptr);
    cache.put(4, four_ptr);
    if (!cache.contains(1))
        cout << "Value cached at 1 has been overwritten." << endl;

    /// with vectors

    LRUCache<Eigen::VectorXcd, map<string, int>*> cache_vector(3);

    Eigen::VectorXcd key(2);
    key(0) = 1;
    key(1) = 0;

    auto* map_value_ptr = new map<string, int>;
    (*map_value_ptr)["1"] = 1;

    cache_vector.put(key, map_value_ptr);
    if (cache_vector.contains(key))
        cout << "Successfully stored vector key." << endl;

    /// with measurement function

    LRUCache<key_type, measure_value_type> measure_cache(1);

    // define key inputs
    Eigen::VectorXcd tuple1(2);
    tuple1(0) = 1;
    tuple1(1) = 0;

    vector<u_int> tuple2;
    tuple2.push_back(0);

    key_type measure_key(tuple1, tuple2);

    // define value
    // convert input indices to idx
    vector<qpp::idx> indices_idx;
    indices_idx.push_back(0);

    // obtain measurement data using qpp
    auto meas_data = qpp::measure(tuple1, qpp::gt.Id(2), indices_idx);
    auto probs = std::get<qpp::PROB>(meas_data);
    auto resultant_states = std::get<qpp::ST>(meas_data);

    // store in cache
    measure_value_type measure_value = make_pair(probs, resultant_states);
    measure_cache.put(measure_key, measure_value);

    // test output
    if (measure_cache.contains(measure_key))
        cout << "Successfully stored measurement value." << endl;
    else
        throw logic_error("Failed to store measurement value.");

    // insert another
    Eigen::VectorXcd new_tuple1(2);
    new_tuple1(0) = 0;
    new_tuple1(1) = 1;

    key_type new_measure_key(new_tuple1, tuple2);

    meas_data = qpp::measure(new_tuple1, qpp::gt.Id(2), indices_idx);
    probs = std::get<qpp::PROB>(meas_data);
    resultant_states = std::get<qpp::ST>(meas_data);

    measure_value = make_pair(probs, resultant_states);
    measure_cache.put(new_measure_key, measure_value);

    // test output
    if (measure_cache.contains(measure_key))
        throw logic_error("Failed to overwrite measurement value.");
    else
        cout << "Successfully overwrote measurement value." << endl;

    /// with apply function

    LRUCache<key_type, apply_value_type> h_cache(1);

    // obtain gate data
    auto apply_key = measure_key;
    auto output_state = qpp::apply(tuple1, qpp::gt.H, {tuple2[0]});
    h_cache.put(apply_key, output_state);

    // test output
    if (h_cache.contains(apply_key))
        cout << "Successfully stored gate value." << endl;
    else
        throw logic_error("Failed to store gate value.");

    // insert another
    auto new_apply_key = new_measure_key;
    output_state = qpp::apply(new_tuple1, qpp::gt.H, {tuple2[0]});
    h_cache.put(new_apply_key, output_state);

    // test output
    if (measure_cache.contains(measure_key))
        throw logic_error("Failed to overwrite gate value.");
    else
        cout << "Successfully overwrote gate value." << endl;
}
