//
//  utils.hpp
//  server
//
//  Created by XIAOLIANG WU on 4/11/21.
//
//  Portions of LRU cache code from Tim Day's "LRU cache implementation in C++"
//  (https://timday.bitbucket.io/lru.html#x1-8007r1) with copyright info below
//
//  Copyright (c) 2010-2011, Tim Day <timday@timday.com>
//
//  Permission to use, copy, modify, and/or distribute this software for any
//  purpose with or without fee is hereby granted, provided that the above
//  copyright notice and this permission notice appear in all copies.
//
//  THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
//  WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
//  MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
//  ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
//  WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
//  ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
//  OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
//

#ifndef utils_hpp
#define utils_hpp

#include <stdio.h>
#include <iostream>
#include <list>
#include <unordered_map>
#include <vector>
#include <mutex>
#include <condition_variable>
#include <Eigen/Dense>

using namespace std;

void int_to_chars(u_long n, char* res);
uint chars_to_int(char* raw_data);
void send_msg_with_length(int socket, string message);
string recv_msg_with_length(int socket);
int rand_int(int low, int high);

template <typename K, typename V> class LRUCache {
public:
    // for multithreading
    mutex cache_mutex;
    condition_variable cache_cv;

    explicit LRUCache(int maxsize)
    {
        size = maxsize;
    }
    bool allocated(K key)
    {
        return cache_aux.count(key) > 0;
    }
    bool contains(K key)
    {
        return cache.count(key) > 0;
    }
    void allocate(K);
    V get(K);
    void put(K, V);

private:
    int size;
    list<K> key_list;
    unordered_map<K, V> cache;
    unordered_map<K, typename list<K>::iterator> cache_aux;
};

#include "utils.tpp"

#endif /* utils_hpp */
