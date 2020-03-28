import argparse
import os
import csv

import pandas as pd

from utils.log import logger
from utils.similarity import get_top_similarity_indices
from utils.utils import text_2_id, get_combinations


class Normalizer:
    def __init__(self, ref_df, wiki_df, output_folder):
        self.ref_df = ref_df
        self.wiki_df = wiki_df
        self.ref_names = {}  # key is ref main name, value is set of wiki concepts
        self.ref_synonyms = {}  # key is synonym, value is set of ref names
        self.wiki_concepts = {}  # key is wiki concept, value is main label
        self.wiki_concepts_inv = {}  # key is main label, value is set of wiki concepts
        self.wiki_synonyms = {}  # key is synonym, value is wiki concept
        self.matches = {}  # key is string, value is set of matching strings
        self.matches_df = None  # for debugging, storing it in folder
        self.output_folder = output_folder


    @staticmethod
    def get_subnames(name):
        '''
        :param name: a sentence
        :return: combination of 2 words minimum, must be anchored at beginning or end, at least one word of the combination has to be bigger than 3 letters
        '''
        words = name.split(" ")
        subnames = set()
        for combination in get_combinations(words, 2):
            big_enough = False
            for word in combination:
                if len(word)>3:
                    big_enough = True
                    break
            if big_enough and (combination[0]==words[0] or combination[len(combination)-1]==words[len(words)-1]):
                subnames.add(" ".join(list(combination)))
        return list(subnames)

    @staticmethod
    def add_name(name, d, identifier):
        if name not in d.keys():
            d[name] = set()
        if identifier is not None:
            d[name].add(identifier)
        combinations = Normalizer.get_subnames(name)
        for combination in combinations:
            combination = text_2_id(combination)
            if combination not in d.keys():
                d[combination] = set()
            if identifier is not None:
                d[combination].add(identifier)

    def set_ref_names(self):
        logger.info("Setting reference names...")
        for k in set(self.ref_df["Name"].unique()):
            k = text_2_id(k)
            self.ref_names[k] = set()
            Normalizer.add_name(k, self.ref_synonyms, k)
        logger.info("Number of athletes={}, Number of names={}".format(len(self.ref_names), len(self.ref_synonyms)))

    def set_wiki_names(self):
        logger.info("Setting wiki names...")
        for i, row in self.wiki_df.iterrows():
            name = row["label"]
            name = text_2_id(name)
            self.wiki_concepts[row["concept"]] = name
            if name not in self.wiki_concepts_inv:
                self.wiki_concepts_inv[name] = set()
            self.wiki_concepts_inv[name].add(row["concept"])
            Normalizer.add_name(name, self.wiki_synonyms, row["concept"])
            for name in row["names"].split("||"):
                name = text_2_id(name)
                Normalizer.add_name(name, self.wiki_synonyms, row["concept"])
        logger.info("...Setting wiki names done!!")

    def find_exact_matches0(self, d1, d2, which_arg_is_wiki, matches):
        for name in d1.keys():
            if name in d2.keys():
                for name1 in d1[name]:
                    for name2 in d2[name]:
                        if which_arg_is_wiki == 1 and name1 not in self.ref_names[name2]:
                            if name2 not in matches:
                                matches[name2] = set()
                            matches[name2].add(self.wiki_concepts[name1])

                        elif which_arg_is_wiki == 2 and name2 not in self.ref_names[name1]:
                            if name1 not in matches:
                                matches[name1] = set()
                            matches[name1].add(self.wiki_concepts[name2])
        return matches

    def find_exact_matches(self):
        logger.info("Starting exact matching normalization...")
        matches = self.find_exact_matches0(self.ref_synonyms, self.wiki_synonyms, 2, {})
        matches = self.find_exact_matches0(self.wiki_synonyms, self.ref_synonyms, 1, matches)
        count_found = 0
        count_not_found = 0
        for k, v in matches.items():
            v = list(v)
            indices = get_top_similarity_indices(k, v, threshold=0.7)
            if indices == []:
                continue
            for i in indices:
                for concept in self.wiki_concepts_inv[v[i]]:
                    self.ref_names[k].add(concept)
                    count_found += 1
        for k, v in self.ref_names.items():
            if len(v) == 0:
                count_not_found += 1
        logger.info("found={}, not_found={}".format(count_found, count_not_found))
        logger.info("...Exact matching normalization done!")

    def normalize(self):

        self.set_wiki_names()
        self.set_ref_names()
        self.find_exact_matches()

        with open(os.path.join(self.output_folder, "matching_athletes.csv"), "w") as f:
            wr = csv.writer(f, delimiter="\t")
            wr.writerow(["ref", "wiki"])
            for k, v in self.ref_names.items():
                wr.writerow([k, "||".join(v)])


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
    df_wiki = df_wiki.fillna("")

    normalizer = Normalizer(df_ref, df_wiki, args["output"])
    normalizer.normalize()
