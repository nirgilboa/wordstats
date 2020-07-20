Wordstats
===========

Counts word frequency in provided strings/urls/files.

Running:
--------

docker-compose up --build

Containers:
    1. wordstats service (Flask)
    2. redis broker & results backend for Celery
    3. redis backend for service
    4. Celery worker

Design:
-------

Counting:
    - Large files are broken into chunks, each chunk is processed in memory.
    - Chunk results (word frequency dicts) are accumulated in a single redis hash.
    - Once processing is complete, the hash name is appended to a redis set of all hashes.

Querying:
    - Aggregate the frequency of a word from all hashes in the set.

Additional:
    - To avoid the set getting too big, a task reduces two hashes at a time into one by merging



API Usage:
==========

Counting
--------

General Assumptions:
    - Words are delimited by spaces
    - Enough local disk space is available to download files from given urls for processing

Strings::

    POST /api/v1/words/count
    Content-Type: application/json
    Example Payload:
    {
        "type": "string",
        "data": "Hi! My name is (what?), my name is (who?), my name is Slim Shady"
    }

Assumptions:
    - Payloads larger than 10MB will be rejected with 413 Payload Too Large
    - Invalid json will be rejected with 400 Bad Request

Files::

    POST /api/v1/words/count
    Content-Type: application/json
    Example Payload:
    {
        "type": "file",
        "data": "/app/text_file.txt"
    }

Assumptions:
    - The OS is \*nix (Windows is not supported)
    - Path provided is local and absolute (/app is mapped to local folder)
    - File encoding is utf-8

Urls::

    POST /api/v1/words/count
    Content-Type: application/json
    Example Payload:
    {
        "type": "url",
        "data": "https://raw.githubusercontent.com/nirgilboa/wordstats/master/text_file.txt"
    }



Querying
---------
::

    POST /api/v1/words/query
    Content-Type: application/json
    Example Payload:
    {
        "word": "Shady",
    }

    Example Response:
    {
        "word": "shady",
        "frequency": "1" (non-existing words will return 0)
    }

Assumptions:
    - Query word is case insensitive (lowercase is returned in answer for clarity)
    - Query word is expected to match [A-Za-z,-]+
