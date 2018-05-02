import sys
import io
from sets import Set

import yaml
import json

from SPARQLWrapper import SPARQLWrapper, JSON
from pymongo import MongoClient

import networkx as nx
from networkx.drawing.nx_agraph import graphviz_layout, to_agraph

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

def getAnimegraphy(seiyu_uri, fromYear, toYear):
	sparql = SPARQLWrapper("http://localhost:8890/sparql")

	queryString = """
	prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
	prefix wdt: <http://www.wikidata.org/prop/direct/> 
	prefix wd: <http://www.wikidata.org/entity/> 

	SELECT ?anime_uri ?start_year
	WHERE {{
		?anime_uri wdt:P725 <{0}>.
		
		?anime_uri wdt:P580 ?start_year.
		FILTER(?start_year >= {1})

		OPTIONAL{{
			?anime_uri wdt:P582 ?end_year.
			FILTER(?end_year <= {2})
		}}
	}}
	""".format(seiyu_uri, fromYear, toYear)

	sparql.setQuery(queryString)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()

	bindings = yaml.load(json.dumps(results["results"]["bindings"]))
	
	works = Set()

	for item in bindings:
		animeUri = item['anime_uri']['value']
		startYear = item['start_year']['value'][:4]

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

def makeGraph(seiyuuList, fromYear, toYear, requiredWorksInCommon):
	client = MongoClient()
	db = client.seiyuuData
	seiyuuCompleteData = db.seiyuu

	G = nx.Graph()
	
	seiyuuWorksDict = {}

	# NODES
	for seiyuu in seiyuuList:
		seiyuUri = seiyuu['seiyu_uri']['value']
		seiyuuData = seiyuuCompleteData.find_one({"id":seiyuUri})
		
		name = seiyuu['seiyu_name']['value']
		popularity = seiyuuData['data']['member_favorites']
		works, debut = getAnimegraphy(seiyuUri, fromYear, toYear)

		seiyuuWorksDict[seiyuUri] = works

		nodeData = {"name": name, "popularity": popularity, "debut": debut}
		G.add_node(seiyuUri, attr_dict=nodeData)

	# EDGES
	for seiyu1, works1 in seiyuuWorksDict.iteritems():
		for seiyu2, works2 in seiyuuWorksDict.iteritems():
			worksInCommon = works1.intersection(works2)
			if seiyu1 < seiyu2 and len(worksInCommon) >= requiredWorksInCommon: #seiyu1 < seiyu2 para que no haya repetidos (mejorar)
				G.add_edge(seiyu1, seiyu2)

	return G

def main(fromYear, toYear, requiredWorksInCommon):
	seiyuuWithAtLeastOneWork = getSeiyuuWithAtLeastOneWork()[:60]

	G = makeGraph(seiyuuWithAtLeastOneWork, fromYear, toYear, requiredWorksInCommon)

	nx.algorithms.clique.find_cliques(G)
	
if __name__ == '__main__':
	fromYear = 0
	toYear = 3000
	requiredWorksInCommon = 1

	if len(sys.argv) >= 4:
		fromYear = int(sys.argv[1])
		toYear = int(sys.argv[2])
		requiredWorksInCommon = int(sys.argv[3])

	main(fromYear, toYear, requiredWorksInCommon)