cmake_minimum_required(VERSION 3.10)
project(quantum_server_cpp)

set(CMAKE_CXX_STANDARD 17)

find_package(Eigen3 3.3 REQUIRED)
find_package(Threads REQUIRED)


add_executable(quantum_server_cpp
        src/main.cpp
        src/circuit.cpp
        src/multi_thread_server.cpp
        src/quantum_manager.cpp
        src/utils.cpp
        src/utils.tpp)

add_executable(test_circuit
        tests/test_circuit.cpp
        src/circuit.cpp
        src/quantum_manager.cpp
        src/utils.cpp
        src/utils.tpp)

add_executable(test_cache
        tests/test_cache.cpp
        src/utils.cpp
        src/utils.tpp)

add_executable(test_hash
        tests/test_hash.cpp
        src/utils.cpp
        src/utils.tpp)

add_executable(test_multithread
        tests/test_multithread.cpp
        src/circuit.cpp
        src/quantum_manager.cpp
        src/utils.cpp
        src/utils.tpp)

target_link_libraries(quantum_server_cpp Eigen3::Eigen)
target_link_libraries(quantum_server_cpp Threads::Threads)
target_link_libraries(test_circuit Eigen3::Eigen)
target_link_libraries(test_circuit Threads::Threads)
target_link_libraries(test_cache Eigen3::Eigen)
target_link_libraries(test_cache Threads::Threads)
target_link_libraries(test_hash Eigen3::Eigen)
target_link_libraries(test_hash Threads::Threads)
target_link_libraries(test_multithread Eigen3::Eigen)
target_link_libraries(test_multithread Threads::Threads)
