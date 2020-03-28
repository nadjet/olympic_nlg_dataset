import itertools
import re
import unicodedata
from collections import Counter

def strip_accents(text):
    """
    Strip accents from input String.

    :param text:^ The input string.
    :type text: String.

    :returns: The processed String.
    :rtype: String.
    """
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore')
    text = text.decode("utf-8")
    return str(text)


def text_to_vector(text):
    WORD = re.compile(r"\w+")
    words = WORD.findall(text)
    return Counter(words)

def text_2_id(text):
    text = re.sub(r"\-"," ", text)
    text = re.sub(r"\([^\)]+\)", "", text)
    text = text.strip()
    #text = strip_accents(text)
    text = re.sub(r"[^a-zA-Z ]+", "", text)  # we remove anything that's not a space or an ascii alphabetical characters
    return text.lower()


def get_combinations(items, sz):
    results = []
    for item in range(0, len(items) + 1):
        for i in itertools.combinations(items, item):
            if len(i) >= sz:
                results.append(i)
    return results


