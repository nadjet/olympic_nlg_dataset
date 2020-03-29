# Olympic NLG Dataset Processing

This repository contains code to obtain a dataset of data and text pairs for NLG. The domain is olympic athletes.

The data comes from a csv of data that was already scraped from a sports platform that can be found [here](https://www.kaggle.com/heesoo37/120-years-of-olympic-history-athletes-and-results). Some additional information is also obtained from DBPedia (2016 Dump), which is date and place of birth/death, nationality, gender and additional names. 

The texts are obtained from the Wikipedia articles. They are the texts just after the infoboxes and before the articles' sections.

The repository includes code to:

- Query the sparql end point.
- Normalize the names in the csv to the dbpedia names.
- Process the xmls with Wikipedia articles to extract the relevant text and then the relevant sentences.
