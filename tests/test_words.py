import json
import re
import time

WORD_COUNT_ENDPOINT = "/api/v1/words/count"
WORD_QUERY_ENDPOINT = "/api/v1/words/query"
CONTENT_TYPE_JSON = {'Content-Type': 'application/json'}


def test_input_format_string(client, app):
    body = {
        'type': 'string',
        'data': 'Hi! My name is (what?), my name is (who?), my name is Slim Shady'
    }
    response = client.post(WORD_COUNT_ENDPOINT, data=json.dumps(body), headers=CONTENT_TYPE_JSON)
    assert response.status_code == 200


def test_input_format_url(client, app):
    body = {
        'type': 'url',
        'data': 'not a good url<>'
    }
    response = client.post(WORD_COUNT_ENDPOINT, data=json.dumps(body), headers=CONTENT_TYPE_JSON)
    assert response.status_code == 400


def test_bad_input(client, app):
    response = client.post(WORD_COUNT_ENDPOINT)
    assert response.status_code == 400
    assert 'Invalid input' in response.json['message']


def test_get_frequency(client, app):
    query_body = {
        'word': 'shady'
    }
    response = client.post(WORD_QUERY_ENDPOINT, data=json.dumps(query_body), headers=CONTENT_TYPE_JSON)
    assert response.status_code == 200
    assert response.json['word'] == 'shady'
    current_frequency = response.json['frequency']

    input_body = {
        'type': 'string',
        'data': 'Hi! My name is (what?), my name is (who?), my name is Slim Shady'
    }
    client.post(WORD_COUNT_ENDPOINT, data=json.dumps(input_body), headers=CONTENT_TYPE_JSON)
    time.sleep(0.1)

    response = client.post(WORD_QUERY_ENDPOINT, data=json.dumps(query_body), headers=CONTENT_TYPE_JSON)
    assert response.status_code == 200
    assert response.json['word'] == 'shady'
    assert response.json['frequency'] == current_frequency+1


def test_input_large_text_test(client, app):
    with open('/home/nirgilbo/Downloads/wordstats/smaller.txt') as file:
        text = file.read()
        input_body = {
            'type': 'string',
            'data': re.escape(text)
        }
        response = client.post(WORD_COUNT_ENDPOINT, data=json.dumps(input_body), headers=CONTENT_TYPE_JSON)
        assert response.status_code == 200


def test_input_file(client, app):
    body = {
        'type': 'file',
        'data': '/home/nirgilbo/Downloads/wordstats/WestburyLab.Wikipedia.Corpus.txt'
    }
    response = client.post(WORD_COUNT_ENDPOINT, data=json.dumps(body), headers=CONTENT_TYPE_JSON)
    assert response.status_code == 200


def test_input_url(client, app, httpserver):
    with open('/home/nirgilbo/Downloads/wordstats/smaller.txt') as file:
        httpserver.expect_request(uri='/big_file').respond_with_data(response_data=file.read())
        body = {
            'type': 'url',
            'data': httpserver.url_for('/big_file')
        }
        response = client.post(WORD_COUNT_ENDPOINT, data=json.dumps(body), headers=CONTENT_TYPE_JSON)
        assert response.status_code == 200
        # Allow background task to download the file
        import time
        time.sleep(1)

