import argparse
import csv
import os
from collections import namedtuple

import pandas as pd

from utils.log import logger
from utils.similarity import get_tfidf_matrix, awesome_cossim_top, get_matches_df
from utils.utils import text_2_id


class WikiConcept:
    def __init__(self, uri: str, identifier: str, main_label: str):
        self.uri = uri
        self.identifier = identifier
        self.main_label = main_label

    def get_main_label(self):
        return self.main_label

    def get_uri(self):
        return self.uri

    def get_identifier(self):
        return self.identifier


class WikiConceptCollection:
    def __init__(self, df):
        self.df = df
        self.id_dict = {}  # key is identifier, value is set of wiki concept
        self.uri_dict = {}  # key is uri, value is set of wiki concept

    def set_dicts(self):
        logger.info("Loading wiki concepts...")
        for i, row in self.df.iterrows():
            concept = row["concept"]
            name = row["label"]
            identifier = text_2_id(name)
            wiki_concept = WikiConcept(concept, identifier, name)
            if identifier not in self.id_dict:
                self.id_dict[identifier] = set()
            if concept not in self.uri_dict:
                self.uri_dict[concept] = set()
            self.id_dict[identifier].add(wiki_concept)
            self.uri_dict[concept].add(wiki_concept)
        logger.info("...Loading {} wiki concepts done!".format(len(self.id_dict)))

    def get_id_dict(self):
        return self.id_dict

    def get_uri_dict(self):
        return self.uri_dict


class Reference:
    def __init__(self, identifier: str, label: str):
        self.identifier = identifier
        self.label = label

    def get_identifier(self):
        return self.identifier

    def get_label(self):
        return self.label


class ReferenceCollection:
    def __init__(self, df):
        self.df = df
        self.id_dict = {}  # key is id, value is set of references

    def set_id_dict(self):
        logger.info("Loading references...")
        for label in set(self.df["Name"].unique()):
            identifier = text_2_id(label)
            reference = Reference(identifier, label)
            if identifier not in self.id_dict:
                self.id_dict[identifier] = set()
            self.id_dict[identifier].add(reference)
        logger.info("...Loading {} references done!".format(len(self.id_dict)))

    def get_id_dict(self):
        return self.id_dict


BasicMatch = namedtuple('BasicMatch', ['match', 'type'])


class Match(BasicMatch):
    def __hash__(self):
        return hash(self.match)

    def __eq__(self, other):
        if not isinstance(other, Match):
            return False
        return other.match == self.match


class Normalizer:
    def __init__(self, ref_df, wiki_df, output_folder):
        self.references = ReferenceCollection(ref_df)
        self.references.set_id_dict()
        self.wiki_concepts = WikiConceptCollection(wiki_df)
        self.wiki_concepts.set_dicts()
        self.output_folder = output_folder

        # key is reference id , value is set of wiki matches
        self.reference_matches = {reference: set() for reference in self.references.get_id_dict()}

        # key is concept id, value is set of reference matches
        self.wiki_matches = {uri: set() for uri in self.wiki_concepts.get_uri_dict()}

    def find_fuzzy_matches(self):
        thresholds = [0.95, 0.90, 0.85, 0.8, 0.75, 0.7]
        for threshold in thresholds:
            logger.info("Fuzzy matching with threshold={}...".format(threshold))
            self.find_fuzzy_matches0(threshold=threshold)
            logger.info("...Fuzzy matching with threshold {} done!".format(threshold))
            self.log_info()

    @staticmethod
    def get_keys(d):
        keys_with_values = set()
        keys_without_values = set()
        for k, v in d.items():
            if len(v) > 0:
                keys_with_values.add(k)
            else:
                keys_without_values.add(k)
        return keys_with_values, keys_without_values

    def log_info(self):
        found_references, not_found_references = Normalizer.get_keys(self.reference_matches)
        found_wikis, not_found_wikis = Normalizer.get_keys(self.wiki_matches)
        logger.info("Number of references={}, found={}, left without matching={}".
                    format(len(self.references.get_id_dict()), len(found_references), len(not_found_references)))
        logger.info("Number of wiki concepts={}, found={}, left without matching={}".
                    format(len(self.wiki_concepts.get_id_dict()), len(found_wikis), len(not_found_references)))

    def add_match0(self, reference, uri, similarity):
        self.reference_matches[reference].add(Match(uri, similarity))
        self.wiki_matches[uri].add(Match(reference, similarity))

    def add_match(self, uri_id, reference_id, similarity):
        wiki_id_dict = self.wiki_concepts.get_id_dict()
        found = 0
        for wiki_concept in wiki_id_dict[uri_id]:
            uri = wiki_concept.get_uri()
            uri_match = Match(uri, similarity)
            if uri_match not in self.reference_matches[reference_id]:
                self.add_match0(reference_id, uri, similarity)
                found += 1
        return found

    @staticmethod
    def get_matches_df(names, threshold):
        logger.info("Total number of names for matrix ={}, first 10={}".format(len(names), names[:10]))
        matrix = get_tfidf_matrix(names)
        logger.info("Computing matches...")
        matches = awesome_cossim_top(matrix, matrix.transpose(), 2,
                                     threshold)  # 2 because one is the similarity of the element with itself
        logger.info("...Computing matches done!")
        matches_df = get_matches_df(matches, names, top=-1)
        logger.info("Before removing full similarity: {}".format(matches_df.shape))
        matches_df = matches_df[matches_df['similarity'] < 0.999999999]  # we remove identity matches (element matching itself), we use 0.99 instead of 1 because of floating point precision
        logger.info("After removing full similarity: {}".format(matches_df.shape))
        return matches_df

    @staticmethod
    def get_unmatched_keys(d):
        items = set()
        for k, v in d.items():
            if len(v) == 0:
                items.add(k)
        return items

    def get_unmatched(self):
        reference_ids = Normalizer.get_unmatched_keys(self.reference_matches)
        wiki_uri_dict = self.wiki_concepts.get_uri_dict()
        wiki_ids = set()
        for uri in Normalizer.get_unmatched_keys(self.wiki_matches):
            for wiki in wiki_uri_dict[uri]:
                wiki_ids.add(wiki.get_identifier())
        return reference_ids, wiki_ids

    def find_fuzzy_matches0(self, threshold=0.7):
        reference_ids, wiki_ids = self.get_unmatched()
        if len(reference_ids) == 0 or len(wiki_ids) == 0:
            logger.info("No values to do fuzzy match with")
            return

        names = list(set(list(reference_ids) + list(wiki_ids)))
        matches_df = Normalizer.get_matches_df(names, threshold)

        num_fuzzy = 0
        records = matches_df.to_records()
        counter = 0
        for _, left_side, right_side, similarity in records:
            if counter % 20000 == 0:
                logger.info(counter)
            counter += 1
            if left_side in reference_ids and right_side in wiki_ids:
                num_fuzzy += self.add_match(right_side, left_side, similarity)
            if right_side in reference_ids and left_side in wiki_ids:
                num_fuzzy += self.add_match(left_side, right_side, similarity)
        logger.info("...{} fuzzy matches found!".format(num_fuzzy))

    def find_exact_matches(self):
        counter = 0
        found = 0
        logger.info("Finding exact matches...")
        references = self.references.get_id_dict()
        wikis = self.wiki_concepts.get_id_dict()
        for identifier in wikis.keys():
            if counter % 100 == 0:
                logger.info(counter)
            counter += 1
            if identifier in references.keys():
                found += self.add_match(identifier, identifier, 1.)
        logger.info("...{} exact matches found!".format(found))

    def normalize(self, output_file="matching_athletes.csv"):
        self.find_exact_matches()
        self.find_fuzzy_matches()
        references = self.references.get_id_dict()
        with open(os.path.join(self.output_folder, output_file), "w") as f:
            wr = csv.writer(f, delimiter="\t")
            wr.writerow(["ref", "uri", "ref_id", "uri_id", "similarity", "#matching_concepts", "#matching_refs"])
            for reference_id in references:
                if reference_id in self.reference_matches.keys():
                    if len(self.reference_matches[reference_id]) == 0:
                        for reference in references[reference_id]:
                            wr.writerow([reference_id, "", reference.get_label()])
                    else:
                        for match in self.reference_matches[reference_id]:
                            uri = match[0]
                            threshold = match[1]
                            for wiki_concept in self.wiki_concepts.get_uri_dict()[uri]:
                                uri_id = wiki_concept.get_identifier()
                                for reference in references[reference_id]:
                                    reference = reference.get_label()
                                    wr.writerow([reference, uri, reference_id, uri_id, threshold,
                                                 len(self.reference_matches[reference_id]), len(self.wiki_matches[match[0]])])


if __name__ == "__main__":
    description_msg = 'Normalizing athlete names to wikipedia uris with basic combinations and name matching, '
    parser = argparse.ArgumentParser(description=description_msg)
    parser.add_argument('-r', '--ref', help='The athletes csv', required=True)
    parser.add_argument('-w', '--wiki', help='The wiki csv', required=True)
    parser.add_argument('-o', '--output', help='The output folder', required=True)
    args = vars(parser.parse_args())
    df_ref = pd.read_csv(args["ref"], sep=",")
    df_ref = df_ref.fillna("")
    df_wiki = pd.read_csv(args["wiki"], sep="\t")
    df_wiki["concept"] = df_wiki["concept"].str.replace("http://dbpedia.org/resource/", "")
    df_wiki = df_wiki.fillna("")

    normalizer = Normalizer(df_ref, df_wiki, args["output"])
    normalizer.normalize()
