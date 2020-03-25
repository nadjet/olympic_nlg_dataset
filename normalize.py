import pandas as pd
import argparse
from utils.similarity import get_tfidf_matrix,awesome_cossim_top, get_matches_df
from utils.log import logger
from utils.utils import text_2_id, get_combinations, flatten
import os

class Normalizer:
    def __init__(self,ref_df,wiki_df, output_folder):
        self.ref_df = ref_df
        self.wiki_df = wiki_df
        self.ref_names = {} # key is ref name, value is set of wiki concepts
        self.ref_synonyms = {} # key is synonym, value is set of ref names
        self.names = {} # key is wiki name, value is wiki concept
        self.matches = {}  # key is string, value is set of matching strings
        self.matches_df = None # for debugging, storing it in folder
        self.output_folder = output_folder

    @staticmethod
    def get_subnames(name):
        return [" ".join(list(combination)) for combination in get_combinations(name.split(" "), 2)]

    @staticmethod
    def add_name(name,d,identifier):
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

    def set_ref_names(self,negative_list=[]):
        logger.info("Setting reference names, negative list={}".format(len(negative_list)))
        for k in set(self.ref_df["Name"].unique()):
            k = text_2_id(k)
            if k in negative_list:
                continue
            self.ref_names[k] = set()
            Normalizer.add_name(k,self.ref_synonyms,k)
        logger.info("Number of athletes={}, Number of names={}".format(len(self.ref_df),len(self.ref_synonyms)))

    def set_wiki_names(self,negative_list=[]):
        logger.info("Setting wiki names, negative list={}".format(len(negative_list)))
        for i,row in self.wiki_df.iterrows():
            if row["concept"] in negative_list:
                continue
            name = row["label"]
            name = text_2_id(name)
            Normalizer.add_name(name,self.names,row["concept"])
            for name in row["names"].split("||"):
                name = text_2_id(name)
                Normalizer.add_name(name,self.names,row["concept"])
        logger.info("...Setting wiki names done!!")

    def set_matches(self):
        logger.info("Setting matches...")
        names = list(self.names.keys())
        for k,v in self.ref_synonyms.items():
            if k in self.ref_names.keys() and len(self.ref_names[k])>0:
                continue
            names.append(k)
            names.extend(list(v))
        names = list(set(names))
        logger.info("Number of names={}".format(len(names)))
        matrix = get_tfidf_matrix(names)
        matches = awesome_cossim_top(matrix, matrix.transpose(), 10, 0.7)
        self.matches_df = get_matches_df(matches, names, top=100000)
        self.matches_df = self.matches_df[self.matches_df['similarity'] < 0.9999999]  # Remove all exact matches

        logger.info("Number of matches={}".format(self.matches_df.shape[0]))
        for i,row in self.matches_df.iterrows():
            if row["left_side"] not in self.matches.keys():
                self.matches[row["left_side"]] = set()
            if row["right_side"] not in self.matches.keys():
                self.matches[row["right_side"]] = set()
            self.matches[row["left_side"]].add(row["right_side"])
            self.matches[row["right_side"]].add(row["left_side"])
        logger.info("...Setting matches done!")

    def find_exact_matches(self):
        logger.info("Starting exact matching normalization...")
        count_found=0
        count_not_found=0
        i=0
        for name in self.ref_names.keys():
            if name in self.names.keys():
                self.ref_names[name].update(self.names[name])
                count_found += 1
            else:
                count_not_found += 1
            if i%100==0:
                logger.info("i={},found={},not_found={}".format(i,count_found, count_not_found))
            i += 1
        logger.info("found={}, not_found={}".format(count_found, count_not_found))
        logger.info("...Exact matching normalization done!")

    def find_fuzzy_matches(self):
        logger.info("Starting fuzzy matching normalization...")
        count_found = 0
        count_not_found = 0
        i = 0
        self.set_matches()
        for name in self.ref_names.keys():
            if len(self.ref_names[name]) > 0:
                continue
            found=False
            if name in self.matches.keys():
                for item in self.matches[name]:
                    if item in self.names.keys():
                        self.ref_names[name].update(self.names[item])
                        found=True
            if found:
                count_found +=1
            else:
                count_not_found += 1
            if i % 100 == 0:
                logger.info("i={},found={}, not_found={}".format(i, count_found,count_not_found))
            i += 1
        logger.info("...Fuzzing matching normalization done!")
        logger.info("found={}, not_found={}".format(count_found, count_not_found))

    def normalize(self,df_match=None):
        if df_match is not None:
            wikis = []
            refs = []
            for i, row in df_match.iterrows():
                if len(row["wiki"]) > 0:
                    wikis.append(row["wiki"])
                    refs.append(row["ref"])
            refs = list(set(refs))
            wikis = list(set(wikis))
            self.ref_synonyms = {}
            self.names = {}
            self.set_ref_names(negative_list=refs)
            self.set_wiki_names(negative_list=wikis)
            self.find_fuzzy_matches()
            new_ref_names = {}
            for i, row in df_match.iterrows():
                if row["ref"] in self.ref_names and len(row["wiki"])>0:
                    logger.info("#Error: {}, {}".format(row["ref"],row["wiki"]))
                elif row["ref"] not in new_ref_names.keys():
                    new_ref_names[row["ref"]] = set()
                if len(row["wiki"])>0:
                    new_ref_names[row["ref"]].add(row["wiki"])
            for k,v in new_ref_names.items():
                if k in self.ref_names:
                    self.ref_names[k].update(v)
                else:
                    self.ref_names[k] = v
        else:
            self.set_wiki_names()
            self.set_ref_names()
            self.find_exact_matches()
            wikis = flatten([list(value) for value in self.ref_names.values()])
            refs = [ref for ref in self.ref_names.keys() if len(self.ref_names[ref]) > 0]
            self.ref_synonyms = {}
            self.names = {}
            self.set_ref_names(negative_list=refs)
            self.set_wiki_names(negative_list=wikis)
            self.find_fuzzy_matches()

        self.matches_df.to_csv(os.path.join(self.output_folder, "matches.csv"), index=False, sep="\t")

        with open(os.path.join(self.output_folder, "matching_athletes.csv"), "w") as f:
            wr = csv.writer(f, delimiter="\t")
            wr.writerow(["ref", "wiki"])
            for k, v in self.ref_names.items():
                wr.writerow([k, "||".join(v)])


import csv

if __name__ == "__main__":
    description_msg = 'Normalizing athlete names to wikipedia uris in 2 stages: (1) with basic combinations and name matching, (2) with tf*idf similarity matrix for the remainders'
    parser = argparse.ArgumentParser(description=description_msg)
    parser.add_argument('-r', '--ref', help='The athletes csv', required=True)
    parser.add_argument('-m', '--match', help='The matching csv')
    parser.add_argument('-w', '--wiki', help='The wiki csv', required=True)
    parser.add_argument('-o', '--output', help='The output folder', required=True)
    args = vars(parser.parse_args())
    df_ref = pd.read_csv(args["ref"],sep=",")
    df_ref = df_ref.fillna("")
    #df_ref = df_ref.sample(10)
    df_wiki = pd.read_csv(args["wiki"],sep="\t")
    df_wiki = df_wiki.fillna("")

    normalizer = Normalizer(df_ref,df_wiki, args["output"])

    df_match = None
    if args["match"] is not None:
        df_match = pd.read_csv(args["match"],sep="\t")
        df_match = df_match.fillna("")

    normalizer.normalize(df_match=df_match)



