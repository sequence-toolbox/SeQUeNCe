#include "multi_thread_server.hpp"

int main(int argc, const char * argv[])
{
    const char * ip = argv[1];
    int port = atoi(argv[2]);
    int client_num = atoi(argv[3]);
    std::string formalism = argv[4];
    std::string log_path = argv[5];
    
    start_server(ip, port, client_num, formalism, log_path);
}
