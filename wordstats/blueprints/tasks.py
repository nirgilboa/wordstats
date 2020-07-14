import tempfile
import uuid
from collections import defaultdict

import requests
from celery import chord

from wordstats import celery
from wordstats.blueprints.file_utils import get_file_chunks, read_chunk
from wordstats.blueprints.redis_utils import write_to_main_hash, write_to_secondary_hash, \
    add_to_main_set, reduce_main_set_if_needed
from wordstats.blueprints.string_utils import spliterator, clean_up_word


@celery.task
def process_file_task(filepath):
    chunks = get_file_chunks(filepath)
    if len(chunks) == 1:
        process_small_file.delay(chunks[0], filepath)
    else:
        hash_name = str(uuid.uuid4())
        tasks = [process_file_chunk.s(chunk, filepath, hash_name) for chunk in chunks]
        callback = update_main_set.s(hash_name)
        chord(tasks)(callback)


@celery.task
def process_small_file(chunk, filepath):
    text = read_chunk(chunk, filepath)
    process_text_task(text)


@celery.task
def update_main_set(chunk_results, hash_name):
    add_to_main_set(hash_name)
    reduce_set.apply_async(countdown=600)
    return True


@celery.task
def process_file_chunk(chunk, filepath, hash_name):
    text = read_chunk(chunk, filepath)
    word_frequency = process_text(text)
    return write_to_secondary_hash(word_frequency, hash_name)


@celery.task
def process_text_task(text):
    words_dict = process_text(text)
    write_to_main_hash(words_dict)
    return True


def process_text(text):
    word_frequency = defaultdict(int)
    for word in spliterator(text):
        word_frequency[clean_up_word(word)] += 1

    return word_frequency


@celery.task
def process_url_task(url):
    file = tempfile.NamedTemporaryFile(mode='wb', delete=False)
    with requests.get(url, stream=True) as req:
        for chunk in req.iter_content(chunk_size=8192):
            file.write(chunk)

    process_file_task.delay(file.name)


@celery.task
def reduce_set():
    reduce_main_set_if_needed()
