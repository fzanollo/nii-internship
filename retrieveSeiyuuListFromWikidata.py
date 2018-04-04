import sys
import io

import yaml
import json

from SPARQLWrapper import SPARQLWrapper, JSON

def getSeiyuuListFromWikidata(limitTo):
	sparql = SPARQLWrapper("https://query.wikidata.org/sparql")

	queryString = """
	SELECT 
		?item 
		(SAMPLE(?label) AS ?itemLabel) 
		(SAMPLE(?MyAnimeList_ID) AS ?MAL_ID) 
	WHERE {
		{?item wdt:P106 wd:Q622807.}

		?item rdfs:label ?label.
		FILTER(LANGMATCHES(LANG(?label), "en"))
		OPTIONAL { ?item wdt:P4084 ?MyAnimeList_ID. }
	}
	GROUP BY ?item
	"""

	if limitTo > 0:
		queryString += "LIMIT {0}".format(limitTo)

	sparql.setQuery(queryString)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()

	bindings = yaml.load(json.dumps(results["results"]["bindings"]))

	outputFile = io.open(outputFileName, 'w', encoding="utf-8")
	outputFile.write(json.dumps(bindings,ensure_ascii=False))

if __name__ == '__main__':
	outputFileName = 'output.json'
	limitTo = 1 # less or equal to 0 implies no limit

	if len(sys.argv) >= 2:
		outputFileName = sys.argv[1] + '.json'

	if len(sys.argv) >= 3:
		limitTo = int(sys.argv[2])

	getSeiyuuListFromWikidata(outputFileName, limitTo)