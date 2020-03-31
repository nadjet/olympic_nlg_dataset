import math
from utils.utils import text_to_vector
# https://bergvca.github.io/2017/10/14/super-fast-string-matching.html
import re
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
import sparse_dot_topn.sparse_dot_topn as ct
from utils.utils import ngrams


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



def get_tfidf_matrix(l):
    vectorizer = TfidfVectorizer(min_df=1, analyzer=ngrams, use_idf=False)
    return vectorizer.fit_transform(l)


def awesome_cossim_top(A, B, ntop, lower_bound=0):
    # force A and B as a CSR matrix.
    # If they have already been CSR, there is no overhead
    A = A.tocsr()
    B = B.tocsr()
    M, _ = A.shape
    _, N = B.shape

    idx_dtype = np.int32

    nnz_max = M * ntop

    indptr = np.zeros(M + 1, dtype=idx_dtype)
    indices = np.zeros(nnz_max, dtype=idx_dtype)
    data = np.zeros(nnz_max, dtype=A.dtype)

    ct.sparse_dot_topn(
        M, N, np.asarray(A.indptr, dtype=idx_dtype),
        np.asarray(A.indices, dtype=idx_dtype),
        A.data,
        np.asarray(B.indptr, dtype=idx_dtype),
        np.asarray(B.indices, dtype=idx_dtype),
        B.data,
        ntop,
        lower_bound,
        indptr, indices, data)

    return csr_matrix((data, indices, indptr), shape=(M, N))


def get_matches_df(sparse_matrix, name_vector, top=100):
    non_zeros = sparse_matrix.nonzero()

    sparserows = non_zeros[0]
    sparsecols = non_zeros[1]

    if top<sparsecols.size and top>-1:
        nr_matches = top
    else:
        nr_matches = sparsecols.size

    left_side = np.empty([nr_matches], dtype=object)
    right_side = np.empty([nr_matches], dtype=object)
    similarity = np.zeros(nr_matches)

    for index in range(0, nr_matches):
        left_side[index] = name_vector[sparserows[index]]
        right_side[index] = name_vector[sparsecols[index]]
        similarity[index] = sparse_matrix.data[index]

    return pd.DataFrame({'left_side': left_side,
                         'right_side': right_side,
                         'similarity': similarity})

