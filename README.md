# Olympic NLG Dataset Processing

This repository contains code to obtain a dataset of data and text pairs for NLG. The domain is olympic athletes.

## The data

The source of the data is DBPedia, Wikipedia and a dataset of scraped Olympic athletes information.

###DBPedia Dump

From the 2016 DBPedia datastore we obtain the uris of +121k olympic athletes with additional personal information: abstract, date and place of birth/death, nationality, gender and additional names. 

###Olympic Athletes Dataset

This dataset can be found [here](https://www.kaggle.com/heesoo37/120-years-of-olympic-history-athletes-and-results). It consists of information about +137k athletes that was scraped by a third party from a sports platform for all the olympic games between 1896 and 2016. It includes every athlete's participation at an olympic game event, with medal won if any. It does not include explicit information about teams or opponents, or competition results (e.g., points).

**Note:** It might be possible to extract some of the information contained in the Olympic Athletes Dataset from the DBPedia Dump via the ontology's categories. However, fine-grained information such as medal won at a specific event, especially if athlete plays in multiple events, is not available from the triplestore.

###Wikipedia article

Wikipedia articles are downloaded from the wikipedia export page [here](https://en.wikipedia.org/wiki/Special:Export) given the list of olympic athletes URIs. These are used in case no olympic-related text is found in the abstract. More specifically, the summary text typically just after the infoboxes and before the article's section is used.
 
## Data processing

The dataset is obtained by following these steps:

1. Query the sparql end point for Athletes uris and information (= all pages whose subject are descendants of the "Olympic competitors" category).
2. Normalize the names in the olympic athletes csv to uris.
3. Extract relevant text from abstracts and/or articles summaries.

### Name normalization

The names in the scraped olympic athlete datasets are not always identical to the DBPedia name. W athlete corrupt in the sense that all characters 
