#include <shared_mutex>
#include <stdexcept>
#include "qpp/qpp.h"

// type definitions for LRUCaches contained in quantum manager
typedef tuple<Eigen::VectorXcd, vector<u_int>>  key_type;
typedef tuple<vector<double>, vector<qpp::cmat>> measure_value_type;
typedef Eigen::VectorXcd apply_value_type;

template <typename T>
void hash_accumulate(T input, size_t* seed)
{
    (*seed) = std::hash<T>()(input) + 0x9e3779b9 + ((*seed) << 6) + ((*seed) >> 2);
}

// custom hash/equal definitions for map
// used for caching vectors/etc. in LRUCache application
namespace std {
    template <>
    struct hash<complex<double>> {
        size_t operator()(complex<double> const& comp) const {
            size_t seed = 0;
            hash_accumulate<double>(comp.real(), &seed);
            hash_accumulate<double>(comp.imag(), &seed);
            return seed;
        };
    };
    template <>
    struct hash<Eigen::VectorXcd> {
        size_t operator()(Eigen::VectorXcd const& matrix) const {
            size_t seed = 0;
            for (size_t i = 0; i < matrix.size(); ++i) {
                auto elem = *(matrix.data() + i);
                hash_accumulate<Eigen::VectorXcd::Scalar>(elem, &seed);
            }
            return seed;
        };
    };
    template <typename T>
    struct hash<vector<T>> {
        size_t operator()(vector<T> const& vect) const {
            size_t seed = 0;
            for (size_t i = 0; i < vect.size(); ++i) {
                T elem = vect[i];
                hash_accumulate<T>(elem, &seed);
            }
            return seed;
        }
    };
    template <>
    struct hash<key_type> {
        size_t operator()(key_type const& args) const {
            Eigen::VectorXcd first; vector<u_int> second;
            tie(first, second) = args;
            size_t seed = 0;
            hash_accumulate<Eigen::VectorXcd>(first, &seed);
            hash_accumulate<vector<u_int>>(second, &seed);
            return seed;
        }
    };

    template <>
    struct equal_to<key_type> {
        bool operator() (const key_type x, const key_type y) const {
            if ((get<0>(x).rows() != get<0>(y).rows()) or (get<0>(x).cols() != get<0>(y).cols()))
                return false;
            return (get<0>(x) == get<0>(y)) and (get<1>(x) == get<1>(y));
        }
    };
}

template<typename K, typename V>
void LRUCache<K, V>::allocate(K key)
{
    // remove old keys if necessary
    if (key_list.size() == size) {
        K old_key = key_list.back();
        cache.erase(old_key);
        cache_aux.erase(old_key);
        key_list.pop_back();
    }

    // mark key as most recently accessed and insert into cache
    auto it = key_list.insert(key_list.begin(), key);
    cache_aux[key] = it;

    if (key_list.size() != cache_aux.size()) {
        // uncomment this to test functionality of algorithm (work in progress)
        throw logic_error("mismatch in list of cache keys and cache map");
    }
}

template<typename K, typename V>
void LRUCache<K, V>::put(K key, V value)
{
    if (!allocated(key))
        allocate(key);
    cache[key] = value;
}

template<typename K, typename V>
V LRUCache<K, V>::get(K key)
{
    auto it_cache = cache.find(key);

    // cache miss
    if (it_cache == cache.end())
        throw invalid_argument("key not assigned in cache");

    // cache hit
    // update key as most recently accessed
    auto it_key = cache_aux[key];
    key_list.splice(key_list.begin(), key_list, it_key);

    // return value
    return it_cache->second;
}
