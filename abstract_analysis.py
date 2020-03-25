import spacy

class AbstractAnalysis:

    def __init__(self):
        self.nlp =  spacy.load("en_core_web_sm")
        doc = self.nlp("He played both for the Kings and the Toronto Maple Leafs over nine seasons and has represented Team Finland twice at the Winter Olympics, winning a bronze medal at the 1998 Nagano Olympics, a silver medal at the 2004 World Cup of Hockey in which Finland lost in the finals to host Canada, and a silver medal at the 2006 Torino Olympics.[1]")
        for token in doc:
            print(token.text, token.pos_, token.dep_)


aa = AbstractAnalysis()
