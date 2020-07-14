import os

import redis
import requests
from flask import Blueprint, request
from requests.exceptions import InvalidURL, MissingSchema
from werkzeug.exceptions import RequestEntityTooLarge

from wordstats import InvalidUsage
from wordstats.blueprints.redis_utils import read_word_frequency, get_redis_client

bp = Blueprint("words", __name__, url_prefix="/api/v1/words")
r = get_redis_client()

MAX_CONTENT_LENGTH = 10 * 1024 * 1024
TEXT = 'string'
FILE = 'file'
URL = 'url'
ACCEPTED_TYPES = [TEXT, FILE, URL]


@bp.route("/count", methods=["POST"])
def count():
    """Counts words in a given string, url or local file

    See README.rst for usage details
    """
    validate_input_format(request)
    input_type = request.json['type']

    if input_type == TEXT:
        text = request.json['data']
        from wordstats.blueprints.tasks import process_text_task
        process_text_task.delay(text)

    elif input_type == URL:
        url = request.json['data']
        if not is_valid_url(url):
            raise InvalidUsage("Invalid input: invalid url provided")

        from wordstats.blueprints.tasks import process_url_task
        process_url_task.delay(url)

    elif input_type == FILE:
        filepath = request.json['data']
        if not os.path.isfile(filepath):
            raise InvalidUsage("Invalid input: cannot open file provided")

        from wordstats.blueprints.tasks import process_file_task
        process_file_task.delay(filepath)

    return "ok", 200


@bp.route("/query", methods=["POST"])
def get_word_frequency():
    if not request.is_json or 'word' not in request.json:
        raise InvalidUsage("Invalid input: see readme for correct usage", status_code=400)

    queried_word = str(request.json['word'])
    lowercase_queries_word = queried_word.lower()
    frequency = read_word_frequency(lowercase_queries_word)

    return {
        'word': lowercase_queries_word,
        'frequency': frequency
    }, 200


def validate_input_format(input_request):
    if not input_request.is_json or 'type' not in input_request.json or 'data' not in input_request.json:
        raise InvalidUsage("Invalid input: see readme for correct usage", status_code=400)
    elif input_request.content_length > MAX_CONTENT_LENGTH:
        raise RequestEntityTooLarge
    elif input_request.json['type'] not in ACCEPTED_TYPES:
        raise InvalidUsage("Invalid input: see readme for correct usage", status_code=400)


def is_valid_url(url):
    try:
        response = requests.get(url)
    except (InvalidURL, MissingSchema):
        return False

    if response.status_code != 200:
        return False
    else:
        return True
