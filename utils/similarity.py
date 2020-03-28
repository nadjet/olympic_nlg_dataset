import math
from utils.utils import text_to_vector


def get_cosine(string1, string2):
    assert(isinstance(string1,str) and (isinstance(string2,str)))
    vec1 = text_to_vector(string1)
    vec2 = text_to_vector(string2)
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum([vec1[x] * vec2[x] for x in intersection])

    sum1 = sum([vec1[x] ** 2 for x in list(vec1.keys())])
    sum2 = sum([vec2[x] ** 2 for x in list(vec2.keys())])
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0
    else:
        return float(numerator) / denominator


def get_top_similarity_indices(reference,terms_list,threshold=0.8):
    best_match_indices = []
    best_sim = 0.
    for i in range(len(terms_list)):
        term = terms_list[i]
        sim = get_cosine(reference,term)
        if sim > best_sim:
            best_sim = sim
            best_match_indices = [i]
        elif sim == best_sim:
            best_match_indices.append(i)
    if best_sim >= threshold:
        return best_match_indices
    else:
        return []
