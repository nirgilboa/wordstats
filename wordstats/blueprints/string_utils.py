import re


def spliterator(text):
    return (x.group(0) for x in re.finditer(r"[A-Za-z,-]+", text))


def clean_up_word(word):
    """ Removes digits and special chars, returns a lowercased word
    Allows comma ',' and dash '-'
    """
    return "".join([char.lower() for char in word if char.isalpha() or char in ['-', ',']])