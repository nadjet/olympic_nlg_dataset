import argparse

from utils.log import logger
from utils.sparql_utils import SparqlUtils


class DBPediaMining:
    '''
        Mining consists in getting subjects first, and then for each subject, its concepts
    '''
    PREFIX_DBO = "PREFIX dbo: <http://dbpedia.org/ontology/> "
    PREFIX_DCT = "PREFIX dct: <http://purl.org/dc/terms/> "
    PREFIX_DBC = "PREFIX dbc: <http://dbpedia.org/resource/Category:> "
    PREFIX_PROP = "PREFIX prop: <http://dbpedia.org/property/> "
    PREFIX_FOAF = "PREFIX foaf: <http://xmlns.com/foaf/0.1/> "

    query = PREFIX_DBC + " SELECT DISTINCT ?subject WHERE { ?subject skos:broader{1,10} dbc:Olympic_competitors .}"
    query_subject = {"query": query, "variables": ["subject"]}

    query = PREFIX_DBO + PREFIX_DBC + PREFIX_PROP + PREFIX_DCT + PREFIX_FOAF +\
            " SELECT DISTINCT " \
            "?concept " \
            "(COALESCE(?label0, '') AS ?label) " \
            "(COALESCE(?gender0, '') AS ?gender) " \
            "(COALESCE(?abstract0, '') AS ?abstract) " \
            "(COALESCE(str(?birth_date1),'') AS ?birth_date) " \
            "(COALESCE(str(?death_date1),'') AS ?death_date) " \
            "(GROUP_CONCAT(distinct str(?name),'||') AS ?names) " \
            "(GROUP_CONCAT(distinct str(?nationality1),'||') AS ?nationality) " \
            "(COALESCE(str(?birth_place1),'') AS ?birth_place) " \
            "(COALESCE(str(?death_place1),'') AS ?death_place) " \
            " WHERE {" \
            "?concept dct:subject <+subject+> . " \
            "?concept rdf:type dbo:Person . " \
            "?concept rdfs:label ?label0 . " \
            "FILTER (lang(?label0) = 'en') " \
            "OPTIONAL {?concept dbo:abstract ?abstract0 . FILTER (lang(?abstract0) = 'en') } " \
            "OPTIONAL {?concept ?predicate_birth_date ?birth_date1 . " \
            "FILTER (?predicate_birth_date IN ( dbo:birthDate, prop:birthDate)) " \
            "FILTER (REGEX(STR(?birth_date1),'[0-9]{4}-[0-9][0-9]?-[0-9][0-9]?')). } " \
            "OPTIONAL {?concept ?predicate_death_date ?death_date1 . " \
            "FILTER (?predicate_death_date IN ( dbo:deathDate, prop:deathDate)) " \
            "FILTER (REGEX(STR(?death_date1),'[0-9]{4}-[0-9][0-9]?-[0-9][0-9]?')). } " \
            "OPTIONAL {?concept foaf:gender ?gender0 . FILTER(lang(?gender0) = 'en')} " \
            "OPTIONAL {?concept foaf:name ?name FILTER(lang(?name) = 'en')}  " \
            "OPTIONAL {?concept ?predicate_birthPlace  ?birth_place0 . " \
            "FILTER (?predicate_birthPlace IN ( dbo:birthPlace, prop:birthPlace)) " \
            "?birth_place0 foaf:name ?birth_place1 FILTER(lang(?birth_place1) = 'en')} " \
            "OPTIONAL {?concept ?predicate_deathPlace ?death_place0  " \
            "FILTER (?predicate_deathPlace IN ( dbo:deathPlace, prop:deathPlace)) " \
            "?death_place0 foaf:name ?death_place1 FILTER(lang(?death_place1) = 'en')} " \
            "OPTIONAL {?concept ?predicate_nationality ?nationality1 " \
            "FILTER (?predicate_nationality IN ( dbo:nationality, prop:nationality))" \
            "} " \
            "}"

    query_all = {"query": query, "variables": ["concept", "label", "abstract", "gender", "birth_date", "death_date",
                                               "names", "birth_place", "death_place", "nationality"]}

    def __init__(self):
        self.medalists = {}


    def set_row(self,row,query):
        i_concept = query["variables"].index("concept")
        concept = row[i_concept]
        self.medalists[concept] = {}
        for i in range(0, len(row)):
            d = self.medalists[concept]
            if len(row[i].strip()) > 0 and query["variables"][i] not in d:
                d[query["variables"][i]] = row[i]

    def set_info(self,query,end_point):
        logger.info("Setting info...")
        rows = DBPediaMining.execute_query(DBPediaMining.query_subject["query"], {}, 0, 0,
                                           variables=DBPediaMining.query_subject["variables"],end_point=end_point)
        subjects = [row[0] for row in rows]

        i = 0
        for subject in subjects:
            i = i + 1
            rows = DBPediaMining.execute_query(query["query"], {"+subject+":subject}, i, len(subjects),
                                               variables=query["variables"],end_point=end_point)
            for row in rows:
                self.set_row(row,query)
        logger.info("...Setting info done!")

    @staticmethod
    def execute_query(query_str, replacement_dict, counter, total, variables=[], end_point="http://localhost:8890/sparql"):
        rows = []
        new_query = query_str
        for k,v in replacement_dict.items():
            new_query = new_query.replace(k, v)
        su = SparqlUtils(new_query, "", variables, end_point=end_point)
        results = su.execute_query(None)
        logger.info("Number of results found={}, {}/{}".format(len(results), counter, total))
        for row in results:
            rows.append(row)
        return rows


import pandas as pd

if __name__ == "__main__":
    description_msg = 'Get all olympic athletes'
    parser = argparse.ArgumentParser(description=description_msg)
    parser.add_argument('-o', '--output', help='The output file', required=True)
    args = vars(parser.parse_args())
    dbpedia_mining = DBPediaMining()
    dbpedia_mining.set_info(DBPediaMining.query_all,end_point="http://localhost:8890/sparql")
    rows = dbpedia_mining.medalists.values()
    df = pd.DataFrame(rows)
    df.to_csv(args["output"], index=False, sep="\t", encoding='utf-8')
