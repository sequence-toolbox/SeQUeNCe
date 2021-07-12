//
//  multi_thread_server.hpp
//  server
//
//  Created by XIAOLIANG WU on 4/11/21.
//

#ifndef multi_thread_server_hpp
#define multi_thread_server_hpp

#include <stdio.h>
#include <string>

void *task(void *);

int start_server(const char *ip_chr, int portNo, int client_num, std::string formalism, std::string log_file);

#endif /* multi_thread_server_hpp */
