import codecs
import os

FILE_CHUNK_SIZE = 16 * 1024 * 1024


def get_file_chunks(filepath):
    """ Returns a list of tuples specifying the beginning and end of a file chunk
    """
    chunks = []
    file_size = os.stat(filepath).st_size
    chunk_start = 0
    chunk_end = FILE_CHUNK_SIZE
    with codecs.open(filepath, mode='r', encoding='utf-8') as fh:
        while chunk_end < file_size:
            chunk_end, next_buffer = read_buffer(fh, chunk_end)
            if not next_buffer:
                chunks.append((chunk_start, chunk_end))
            for char in next_buffer:
                if char != u' ':
                    char_length = len(char.encode('utf-8'))
                    chunk_end += char_length
                else:
                    chunks.append((chunk_start, chunk_end))
                    chunk_start = chunk_end
                    chunk_end = chunk_start + FILE_CHUNK_SIZE
                    break
    if len(chunks) == 0:
        chunks.append((0, file_size))
    return chunks


def read_buffer(file_handle, position):
    """ Reads a buffer, resilient to landing in the middle of a unicode string
    """
    for i in range(1, 7):
        potential_chunk_end = position - i
        file_handle.seek(potential_chunk_end)
        try:
            next_buffer = file_handle.read(4096)
            return potential_chunk_end, next_buffer
        except UnicodeDecodeError:
            pass


def read_chunk(chunk, filepath):
    chunk_start, chunk_end = chunk
    with codecs.open(filepath, mode='rb', encoding='utf-8') as fh:
        fh.seek(chunk_start)
        return fh.read(chunk_end - chunk_start)