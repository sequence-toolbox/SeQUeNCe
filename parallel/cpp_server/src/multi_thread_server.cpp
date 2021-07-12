//
//  multi_thread_server.cpp
//  server
//
//  Created by XIAOLIANG WU on 4/11/21.
//

#include "multi_thread_server.hpp"
#include "utils.hpp"
#include "nlohmann/json.hpp"
#include "quantum_manager.hpp"

#include <string.h>
#include <unistd.h>
#include <stdio.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <iostream>
#include <strings.h>
#include <stdlib.h>
#include <string>
#include <pthread.h>
#include <arpa/inet.h>
#include <map>
#include <algorithm>    // std::sort
#include <Eigen/Core>


using namespace std;
using json = nlohmann::json;


void* task(void *);

static int connFd;
map<string, mutex> locks;
QuantumManager qm;

struct task_args {
    int socket;
};

int start_server(const char *ip_chr, int portNo, int client_num, string formalism, string log_file)
{
    Eigen::initParallel();

    int listenFd;
    socklen_t len; //store size of the address
    struct sockaddr_in svrAdd, clntAdd;
    
    pthread_t threadA[client_num];
        
    if((portNo > 65535) || (portNo < 2000))
    {
        cerr << "Please enter a port number between 2000 - 65535" << endl;
        return 0;
    }
    
    //create socket
    listenFd = socket(AF_INET, SOCK_STREAM, 0);
    
    if(listenFd < 0)
    {
        cerr << "Cannot open socket" << endl;
        return 0;
    }
    
    bzero((char*) &svrAdd, sizeof(svrAdd));
    
    svrAdd.sin_family = AF_INET;
    svrAdd.sin_addr.s_addr = inet_addr(ip_chr);
    svrAdd.sin_port = htons(portNo);
    
    //bind socket
    if(::bind(listenFd, (struct sockaddr *)&svrAdd, sizeof(svrAdd)) < 0)
    {
        cerr << "Cannot bind" << endl;
        return 0;
    }
    
    listen(listenFd, client_num);
    
    len = sizeof(clntAdd);
    
    int noThread = 0;

    cout << "Listening at " << ip_chr << ":" << portNo << endl;

    while (noThread < client_num)
    {

        //this is where client connects. svr will hang in this mode until client conn
        connFd = accept(listenFd, (struct sockaddr *)&clntAdd, &len);

        if (connFd < 0)
        {
            cerr << "Cannot accept connection" << endl;
            return 0;
        }

        struct task_args* args = (struct task_args*)malloc(sizeof(struct task_args));
        args->socket = connFd;
        pthread_create(&threadA[noThread], NULL, task, (void *)args);
        
        noThread++;
    }
    
    for(int i = 0; i < noThread; i++)
    {
        pthread_join(threadA[i], NULL);
    }
    
    return 0;
}

mutex locks_lock;

void* task (void *args)
{
    int socket = ((struct task_args*) args)->socket;
    cout << "Thread No: " << pthread_self() << "socket: " << socket << endl;
    bool running = true;
    while(running)
    {
        std::string message = recv_msg_with_length(socket);

        auto msg_json = json::parse(message);
        for (const auto& m: msg_json){
            vector<string> all_keys;

            for (const string key: m["keys"])
            {
                if (qm.exist(key)) {
                    State * state = qm.get(key);
                    for (string k: state->keys){
                        if (find(all_keys.begin(), all_keys.end(), k) == all_keys.end()){
                            all_keys.push_back(k);
                        }
                    }
                } else {
                    locks_lock.lock();
                    mutex * l = &locks[key];
                    locks_lock.unlock();
                }
            }

            sort(all_keys.begin(), all_keys.end());

            for (const auto& key: all_keys) {
                mutex * l = &locks[key];
                l->lock();
            }

            auto type = (std::string)m["type"];

            if (type == "SET")
            {
                vector<string> ks = m["keys"];
                vector<double> amplitudes = m["args"]["amplitudes"];
                qm.set(ks, amplitudes);
            }
            else if (type == "GET")
            {
                string key = m["keys"][0];
                State * state = qm.get(key);
                send_msg_with_length(socket, state->serialization());
            }
            else if (type == "RUN")
            {
                auto circuit = new Circuit(m["args"]["circuit"]);
                vector<string> keys = m["args"]["keys"];
                float meas_samp = m["args"]["meas_samp"];
                map<string, int> res = qm.run_circuit(circuit, keys, meas_samp);
                if (!res.empty()) {
                    json j_res = res;
                    send_msg_with_length(socket, j_res.dump());
                }
            }
            else if (type == "CLOSE")
            {
                running = false;
                break;
            }else if (type == "SYNC")
            {
                json j_res = true;
                send_msg_with_length(socket, j_res.dump());
            }
            else
            {
                printf("Receive unknown type of message %s", type.c_str());
            }

            for (const auto& key: all_keys) {
                locks[key].unlock();
            }
        }
    }
    cout << "\nClosing thread and conn" << endl;
    close(socket);
    return nullptr;
}
