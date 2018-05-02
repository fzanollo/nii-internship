import sys
import io

import yaml
import json

from sets import Set
from SPARQLWrapper import SPARQLWrapper, JSON
from pymongo import MongoClient

def getSeiyuuWithAtLeastOneWork():
	sparql = SPARQLWrapper("http://localhost:8890/sparql")

	queryString = """
	prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
	prefix wdt: <http://www.wikidata.org/prop/direct/> 
	prefix wd: <http://www.wikidata.org/entity/> 

	SELECT ?seiyu_uri ?seiyu_name
	WHERE {
		?seiyu_uri wdt:P106 wd:Q622807.
		?seiyu_uri rdfs:label ?seiyu_name.
		?anime_uri wdt:P725 ?seiyu_uri.
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
	prefix wd: <http://www.wikidata.org/entity/> 

	SELECT ?anime_uri ?start_date
	WHERE {{
		?anime_uri wdt:P725 <{0}>.
		?anime_uri wdt:P580 ?start_date.
	}}
	""".format(seiyu_uri)

	sparql.setQuery(queryString)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()

	bindings = yaml.load(json.dumps(results["results"]["bindings"]))
	
	works = Set()

	for item in bindings:
		animeUri = item['anime_uri']['value']
		startYear = item['start_date']['value'][:4]

		if startYear != "None":
			startYear = int(startYear)
		else:
			startYear = None

		works.add((animeUri, startYear))
	
	debut = getMinimumYear(works)
	return works, debut

def getMinimumYear(works):
	debut = 3000

	for work in works:
		if work[1] != None and work[1] < debut:
			debut = work[1]

	if debut == 3000:
		debut = None

	return debut

def main(nodesFileName, edgesFileName, requiredWorksInCommon):
	nodesFile = io.open(nodesFileName, 'w', encoding="utf-8")
	edgesFile = io.open(edgesFileName, 'w', encoding="utf-8")

	client = MongoClient()
	db = client.seiyuuData
	seiyuuCompleteData = db.seiyuu

	seiyuuWithAtLeastOneWork = getSeiyuuWithAtLeastOneWork()
	# {'seiyu_uri': {'type': 'uri', 'value': 'http://www.wikidata.org/entity/Q49524'}}
	
	seiyuuWorksDict = {}

	# NODES
	nodesFile.write(u'Id,Label,Popularity,Debut\n')
	for item in seiyuuWithAtLeastOneWork:
		seiyuUri = item['seiyu_uri']['value']
		seiyuName = item['seiyu_name']['value']

		seiyuuData = seiyuuCompleteData.find_one({"id":seiyuUri})
		seiyuPopularity = seiyuuData['data']['member_favorites']

		if seiyuUri not in seiyuuWorksDict:
			works, debut = getAnimegraphy(seiyuUri)
			seiyuuWorksDict[seiyuUri] = works

			nodesFile.write(u'{0},{1},{2},{3}\n'.format(seiyuUri, seiyuName, seiyuPopularity, debut))

	# EDGES
	edgesFile.write(u'Source,Target,Type,Id,Weight,Since\n')
	edgeID = 0
	for seiyu1, works1 in seiyuuWorksDict.iteritems():
		for seiyu2, works2 in seiyuuWorksDict.iteritems():
			worksInCommon = works1.intersection(works2)
			if seiyu1 < seiyu2 and len(worksInCommon) >= requiredWorksInCommon: #seiyu1 < seiyu2 para que no haya repetidos (ver si esta bien / mejorar)
				edgesFile.write(u'{0},{1},Undirected,{2},1,{3}\n'.format(seiyu1, seiyu2, edgeID, getMinimumYear(worksInCommon)))
				edgeID += 1

if __name__ == '__main__':
	nodesFileName = 'nodesFile.csv'
	edgesFileName = 'edgesFile.csv'
	requiredWorksInCommon = 0

	if len(sys.argv) >= 2:
		nodesFileName = sys.argv[1] + '.csv'

	if len(sys.argv) >= 3:
		edgesFileName = sys.argv[2] + '.csv'
	
	if len(sys.argv) >= 4:
		requiredWorksInCommon = int(sys.argv[3])

	main(nodesFileName, edgesFileName, requiredWorksInCommon)