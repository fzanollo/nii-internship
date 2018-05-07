import sys
import io

import yaml
import json

from SPARQLWrapper import SPARQLWrapper, JSON

def outputPrefixes():
	prefixes = [('rdfs', 'http://www.w3.org/2000/01/rdf-schema#'), ('wdt', 'http://www.wikidata.org/prop/direct/'), ('wd','http://www.wikidata.org/entity/')]
	prefixesForOutput = u''

	for prefix in prefixes:
		prefixesForOutput += u'@prefix {0}: <{1}> .\n'.format(prefix[0], prefix[1])

	prefixesForOutput += u'\n'
	return prefixesForOutput

def getDebut(seiyuuUri):
	sparql = SPARQLWrapper("http://localhost:8890/sparql")

	query = """
		SELECT ?debut
		{{
			?anime_uri wdt:P725 <{0}>.
			?anime_uri wdt:P580 ?debut.
		}}
		ORDER BY ASC(?debut) LIMIT 1
		""".format(seiyuuUri)

	sparql.setQuery(query)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()

	bindings = yaml.load(json.dumps(results["results"]["bindings"]))

	debut = None

	if len(bindings) > 0:
		debut = bindings[0]['debut']['value']

	return debut

def main(inputFileName, outputFileName):
	seiyuus = yaml.load(io.open(inputFileName, 'r', encoding="utf-8"))

	outputFile = io.open(outputFileName, 'w', encoding="utf-8")
	outputFile.write(outputPrefixes())

	for seiyuu in seiyuus:
		seiyuuUri = seiyuu['seiyu_uri']['value']
		
		debut = getDebut(seiyuuUri)

		if debut != None:
			# seiyu_uri wdt:work_period(start) debut
			outputFile.write(u'<{0}> {1} {2} .\n'.format(seiyuuUri, "wdt:P2031", debut))
			outputFile.write(u'\n')

if __name__ == '__main__':
	inputFileName = 'output.json'
	outputFileName = 'output.ttl'

	if len(sys.argv) >= 3:
		inputFileName = sys.argv[1]
		outputFileName = sys.argv[2] + '.ttl'

	main(inputFileName, outputFileName)