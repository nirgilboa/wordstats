import os
import uuid

import redis
from redis import WatchError

WORDSTATS_MAIN_HASH_NAME = 'wordstats'
WORDSTATS_SET_ALL_HASHES_NAME = 'wordstats-sets'
MAXIMAL_SET_SIZE = 100


def write_to_main_hash(word_dict):
    """ Update the main hash storing word frequencies using a transaction
    """
    r = get_redis_client()

    success = False
    retries = 0
    while not success and retries < 10:
        try:
            p = r.pipeline()
            p.watch(*list(word_dict))

            p.multi()
            for word, freq in word_dict.items():
                p.hincrby(name=WORDSTATS_MAIN_HASH_NAME, key=word, amount=freq)

            p.execute()
            success = True
        except WatchError:
            retries += 1
    return success


def write_to_secondary_hash(word_dict, hash_name):
    """ Accumulates a temporary result into the given hash_name
    """
    r = get_redis_client()

    for word, freq in word_dict.items():
        r.hincrby(name=hash_name, key=word, amount=freq)

    return True


def add_to_main_set(hash_name):
    """ Adds the hash name into the main set of hashes, which in aggregate represent the current word statistics
    """
    r = get_redis_client()

    success = False
    retries = 0
    while not success and retries < 10:
        try:
            p = r.pipeline()
            p.watch(WORDSTATS_SET_ALL_HASHES_NAME)
            p.multi()
            p.sadd(WORDSTATS_SET_ALL_HASHES_NAME, hash_name)
            p.execute()
            success = True
        except WatchError:
            retries += 1
    return success


def read_word_frequency(word):
    """ Returns the total word frequency found in all hashes pointed to by the main result set
    """
    r = get_redis_client()

    all_hash_names = [WORDSTATS_MAIN_HASH_NAME]
    cur, hash_names = r.sscan(WORDSTATS_SET_ALL_HASHES_NAME, cursor=0, count=1)
    all_hash_names += hash_names
    while cur != 0:
        cur, hash_names = r.sscan(WORDSTATS_SET_ALL_HASHES_NAME, cursor=cur, count=1)
        all_hash_names += hash_names

    total_frequency = 0
    for hash_name in all_hash_names:
        freq = 0
        freq = r.hget(name=hash_name, key=word)
        if freq is not None:
            total_frequency += int(freq)

    return total_frequency


def reduce_hashes(first_hash_name, second_hash_name):
    """ Merges two redis hashes containing word frequencies into a new one,
        then replaces the originals with single hash in the main result set
    """
    r = get_redis_client()
    new_hash_name = str(uuid.uuid4())

    _aggregate_word_frequencies(src=first_hash_name, dst=new_hash_name, redis_client=r)
    _aggregate_word_frequencies(src=second_hash_name, dst=new_hash_name, redis_client=r)

    success = False
    retries = 0
    while not success and retries < 10:
        try:
            p = r.pipeline()
            p.watch(WORDSTATS_SET_ALL_HASHES_NAME)
            p.multi()
            p.srem(WORDSTATS_SET_ALL_HASHES_NAME, first_hash_name)
            p.srem(WORDSTATS_SET_ALL_HASHES_NAME, second_hash_name)
            p.sadd(WORDSTATS_SET_ALL_HASHES_NAME, new_hash_name)
            p.execute()
            success = True
        except WatchError:
            retries += 1
    return success


def _aggregate_word_frequencies(src, dst, redis_client):
    cur, word_freq = redis_client.hscan(name=src, cursor=0, count=1000)
    for word_bytes, freq_bytes in word_freq.items():
        redis_client.hincrby(name=dst, key=word_bytes, amount=freq_bytes)

    while cur != 0:
        cur, word_freq = redis_client.hscan(name=src, cursor=cur, count=1000)
        for word_bytes, freq_bytes in word_freq.items():
            redis_client.hincrby(name=dst, key=word_bytes, amount=freq_bytes)


def _get_main_set_size(redis_client):
    return redis_client.scard(WORDSTATS_SET_ALL_HASHES_NAME)


def reduce_main_set_if_needed():
    """ Reduces main set to avoid impacting query performance
    """
    r = get_redis_client()
    if _get_main_set_size(r) < MAXIMAL_SET_SIZE:
        return

    hash_names = r.spop(name=WORDSTATS_SET_ALL_HASHES_NAME, count=2)
    reduce_hashes(hash_names[0], hash_names[1])


def get_redis_client():
    return redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=int(os.getenv('REDIS_PORT', '6380')), db=0)
