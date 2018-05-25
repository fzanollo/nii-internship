import sys
import io
from sets import Set

import yaml
import json

from SPARQLWrapper import SPARQLWrapper, JSON
from pymongo import MongoClient

import networkx as nx
import matplotlib.pyplot as plt
from networkx.drawing.nx_agraph import graphviz_layout, to_agraph

def querySPARQLEndpoint(query):
	sparql = SPARQLWrapper("http://localhost:8890/sparql")

	sparql.setQuery(query)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()

	bindings = yaml.load(json.dumps(results["results"]["bindings"]))

	return bindings

def getSeiyuuList(fromYear, toYear):
	return querySPARQLEndpoint("""
		SELECT ?seiyu_uri ?seiyu_name ?debut
		WHERE {{
			?seiyu_uri wdt:P106 wd:Q622807.
			?seiyu_uri rdfs:label ?seiyu_name.
			?anime_uri wdt:P725 ?seiyu_uri.
			?seiyu_uri wdt:P2031 ?debut.

			filter(?debut >= {0} && ?debut <= {1})
		}} group by ?seiyu_uri
		""".format(fromYear, toYear))

def getAnimegraphy(seiyuUri, fromYear, toYear, animeCollection):
	animes = querySPARQLEndpoint("""
		SELECT ?anime_uri ?start_year
		WHERE {{
			?anime_uri wdt:P725 <{0}>.
			
			?anime_uri wdt:P580 ?start_year.
			FILTER(?start_year >= {1})
		}}
		""".format(seiyuUri, fromYear))

	works = {}
	for item in animes:
		animeUri = item['anime_uri']['value']
		startYear = item['start_year']['value']
		popularity = animeCollection.find_one({"id":animeUri})['data']['favorites']

		works[animeUri] = {'startYear': startYear, 'popularity': popularity}
	
	return works

def makeGraph(seiyuuList, fromYear, toYear, requiredWorksInCommon):
	client = MongoClient()
	db = client.seiyuuData
	seiyuuCollection = db.seiyuu
	animeCollection = db.anime

	G = nx.Graph()
	
	seiyuuWorksDict = {}

	# NODES
	for seiyuu in seiyuuList:
		seiyuUri = seiyuu['seiyu_uri']['value']
		seiyuuData = seiyuuCollection.find_one({"id":seiyuUri})['data']
		
		name = seiyuu['seiyu_name']['value']
		debut = seiyuu['debut']['value']
		popularity = seiyuuData['member_favorites']
		works = getAnimegraphy(seiyuUri, fromYear, toYear, animeCollection)

		seiyuuWorksDict[seiyuUri] = Set(works.keys())

		G.add_node(seiyuUri, label= name, popularity= popularity, debut= debut, works = works)

	# EDGES
	for seiyu1, works1 in seiyuuWorksDict.iteritems():
		for seiyu2, works2 in seiyuuWorksDict.iteritems():
			worksInCommon = works1.intersection(works2)
			if seiyu1 < seiyu2 and len(worksInCommon) >= requiredWorksInCommon: #seiyu1 < seiyu2 para que no haya repetidos (mejorar)
				G.add_edge(seiyu1, seiyu2)

	return G

def main(requiredWorksInCommon, fromYear, toYear):
	seiyuuList = getSeiyuuList(fromYear, toYear)
	
	# MAKE GRAPH
	G = makeGraph(seiyuuList, fromYear, toYear, requiredWorksInCommon)
	
	# SAVE IT
	nx.write_gexf(G, "graphs/atLeast{0}Works_{1}-{2}_V2.gexf".format(requiredWorksInCommon, fromYear, toYear))
	
	
if __name__ == '__main__':
	requiredWorksInCommon = 1
	fromYear = 1960
	toYear = 2018

	if len(sys.argv) >= 2:
		requiredWorksInCommon = int(sys.argv[1])
		
	if len(sys.argv) >= 3:
		fromYear = int(sys.argv[2])

	if len(sys.argv) >= 4:
		toYear = int(sys.argv[3])
		
	main(requiredWorksInCommon, fromYear, toYear)