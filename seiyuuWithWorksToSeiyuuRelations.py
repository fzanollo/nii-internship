import sys
import io

import yaml
import json

from sets import Set

from SPARQLWrapper import SPARQLWrapper, JSON

def getSeiyuuWithAtLeastOneWork():
	sparql = SPARQLWrapper("http://localhost:8890/sparql")

	queryString = """
	prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
	prefix wdt: <http://www.wikidata.org/prop/direct/> 
	prefix jikan: <https://api.jikan.me/> 
	prefix wd: <http://www.wikidata.org/entity/> 

	SELECT ?seiyu_uri
	WHERE {
		?seiyu_uri wdt:P106 wd:Q622807.
		?seiyu_uri wdt:P463 ?anime_uri.
	}group by ?seiyu_uri
	"""

	sparql.setQuery(queryString)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()

	bindings = yaml.load(json.dumps(results["results"]["bindings"]))

	return bindings

def getAnimegraphy(seiyu_uri):
	sparql = SPARQLWrapper("http://localhost:8890/sparql")

	queryString = """
	prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
	prefix wdt: <http://www.wikidata.org/prop/direct/> 
	prefix jikan: <https://api.jikan.me/> 
	prefix wd: <http://www.wikidata.org/entity/> 

	SELECT ?anime_uri
	WHERE {{
		<{0}> wdt:P463 ?anime_uri.
	}}
	""".format(seiyu_uri)

	sparql.setQuery(queryString)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()

	bindings = yaml.load(json.dumps(results["results"]["bindings"]))
	
	works = Set()
	for item in bindings:
		anime_uri = item['anime_uri']['value']
		works.add(anime_uri)

	return works

def main(nodesFileName, edgesFileName):
	nodesFile = io.open(nodesFileName, 'w', encoding="utf-8")
	edgesFile = io.open(edgesFileName, 'w', encoding="utf-8")

	seiyuuWithAtLeastOneWork = getSeiyuuWithAtLeastOneWork()
	# {'seiyu_uri': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/Q49524'}}
	
	seiyuuWorksDict = {}

	# NODES
	nodesFile.write(u'Id,Label,timeset\n')
	nodeID = 0
	for item in seiyuuWithAtLeastOneWork:
		seiyu_uri = item['seiyu_uri']['value']

		if seiyu_uri not in seiyuuWorksDict:
			seiyuuWorksDict[seiyu_uri] = getAnimegraphy(seiyu_uri)

			nodesFile.write(u'{0},{1},\n'.format(nodeID, seiyu_uri))
			nodeID += 1

	# EDGES
	edgesFile.write(u'Source,Target,Type,Id,Label,timeset,Weight\n')
	edgeID = 0
	for seiyu1, works1 in seiyuuWorksDict.iteritems():
		for seiyu2, works2 in seiyuuWorksDict.iteritems():
			if seiyu1 < seiyu2 and len(works1.intersection(works2)) > 0: #seiyu1 < seiyu2 para que no haya repetidos (ver si esta bien / mejorar)
				edgesFile.write(u'{0},{1},Undirected,{2},,,1\n'.format(seiyu1, seiyu2, edgeID))
				edgeID += 1

if __name__ == '__main__':
	nodesFileName = 'nodesFile.csv'
	edgesFileName = 'edgesFile.csv'

	if len(sys.argv) >= 2:
		nodesFileName = sys.argv[1] + '.csv'

	if len(sys.argv) >= 3:
		edgesFileName = sys.argv[2] + '.csv'

	main(nodesFileName, edgesFileName)