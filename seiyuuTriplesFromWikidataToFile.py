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
	return bindings

def seiyuInfoToTriples(seiyu):
	output = u'\n'

	# seiyu_uri wdt:instance_of wd:human
	output += u'<{0}> {1} {2} .\n'.format(seiyu['item']['value'], 'wdt:P31', 'wd:Q5')

	# seiyu_uri wdt:occupation wd:seiyu
	output += u'<{0}> {1} {2} .\n'.format(seiyu['item']['value'], 'wdt:P106', 'wd:Q622807')

	# seiyu_uri rdfs:label name
	output += u'<{0}> {1} "{2}"@{3} .\n'.format(seiyu['item']['value'], "rdfs:label", seiyu['itemLabel']['value'], seiyu['itemLabel']['xml:lang'])

	# seiyu_uri wdt:mal_id mal_id
	if 'MAL_ID' in seiyu:
		output += u'<{0}> {1} <{2}> .\n'.format(seiyu['item']['value'], "wdt:P4084", 'jikan:person/' + seiyu['MAL_ID']['value'])

	return output

def prefixes():
	prefixes = [('rdfs', 'http://www.w3.org/2000/01/rdf-schema#'), ('wdt', 'http://www.wikidata.org/prop/direct/'), ('jikan', 'https://api.jikan.me/' ),('wd','http://www.wikidata.org/entity/')]
	prefixesForOutput = u''

	for prefix in prefixes:
		prefixesForOutput += u'@prefix {0}: <{1}> .\n'.format(prefix[0], prefix[1])

	return prefixesForOutput

def main(outputFileName, limitTo):
	seiyus = getSeiyuuListFromWikidata(limitTo)

	print('* Seiyu list received from wikidata *')

	outputFile = io.open(outputFileName, 'w', encoding="utf-8")
	outputFile.write(prefixes())

	for seiyu in seiyus:
		outputFile.write(seiyuInfoToTriples(seiyu))

if __name__ == '__main__':
	outputFileName = 'output.ttl'
	limitTo = 1 # less or equal to 0 implies no limit

	if len(sys.argv) >= 2:
		outputFileName = sys.argv[1] + '.ttl'

	if len(sys.argv) >= 3:
		limitTo = int(sys.argv[2])

	main(outputFileName, limitTo)