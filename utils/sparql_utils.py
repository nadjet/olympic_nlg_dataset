import re
from SPARQLWrapper import SPARQLWrapper, JSON
from utils.log import logger
import pandas as pd
import csv


class SparqlUtils:


    def __init__(self,query,prefix,variables,end_point="http://localhost:8890/sparql"):
        self.sparql = SPARQLWrapper(end_point)
        self.query = query
        if prefix is None:
            self.prefix = ""
        else:
            self.prefix = prefix
        self.variables = variables

    def fill_query_values(self, values_dict):
        new_query = self.query
        for key,value in values_dict.items():
            value = self.prefix + value
            new_query = new_query.replace(key,value)
        return new_query

    def set_results(self, results):
        if "boolean" in results:
            return results["boolean"]
        new_values = []
        for binding in results['results']['bindings']:
            binding_result = []
            for variable in self.variables:
                if variable in binding:
                    result = binding[variable]
                    result['value'] = result['value'].replace(self.prefix, "")
                    result['value'] = result['value'].replace("\n", "\\n")  # escaping new line
                    binding_result.append(result['value'])
            new_values.append(binding_result)
        return new_values

    def execute_query(self, value):
        try:
            if value is not None and isinstance(value,str):
                value = self.prefix + value
                new_query = re.sub(r"\+[^\+]+\+", value, self.query)
            elif value is not None and isinstance(value,dict):
                new_query = self.fill_query_values(value)
            else:
                new_query = self.query
            self.sparql.setQuery(new_query)
            self.sparql.setReturnFormat(JSON)
            try:
                results = self.sparql.query().convert()
                if results["results"]["bindings"]==0:
                    print(new_query,results)
                return self.set_results(results)
            except Exception as e:
                print(e)
                return []
        except:
            logger.debug("##Error executing query with: {}".format(value))
            return set()



