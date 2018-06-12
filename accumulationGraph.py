import sys
from sets import Set

import yaml
import json

from SPARQLWrapper import SPARQLWrapper, JSON
from pymongo import MongoClient

import networkx as nx

client = MongoClient()
db = client.seiyuuData
seiyuuCollection = db.seiyuu
animeCollection = db.anime

def querySPARQLEndpoint(query):
	sparql = SPARQLWrapper("http://localhost:8890/sparql")

	sparql.setQuery(query)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()

	bindings = yaml.load(json.dumps(results["results"]["bindings"]))

	return bindings

def getSeiyuusWithDebutIn(year):
	return querySPARQLEndpoint("""
		SELECT ?seiyuu_uri ?seiyuu_name ?debut ?gender ?birthday ?birthplace
		WHERE {{
			?seiyuu_uri wdt:P106 wd:Q622807.
			?seiyuu_uri rdfs:label ?seiyuu_name.			
			?seiyuu_uri wdt:P2031 ?debut.
			?seiyuu_uri wdt:P21 ?gender.

			optional{{?seiyuu_uri wdt:P569 ?birthday.}}
			optional{{?seiyuu_uri wdt:P19 ?birthplace.}}

			filter(?debut = {0})
		}} group by ?seiyuu_uri
		""".format(year))

def getAnimegraphyStartingIn(seiyuuUri, year):
	animes = querySPARQLEndpoint("""
		SELECT ?anime_uri ?start_year
		WHERE {{
			?anime_uri wdt:P725 <{0}>.
			
			?anime_uri wdt:P580 ?start_year.
			FILTER(?start_year >= {1})
		}}
		""".format(seiyuuUri, year))

	works = {}
	for item in animes:
		animeUri = item['anime_uri']['value']
		animeData = animeCollection.find_one({"id":animeUri})

		startYear = item['start_year']['value']
		favorites = animeData['favorites']
		score = animeData['score']
		popularity = animeData['popularity']

		genres = []
		for genre in animeData['genre']:
			genres.append(genre['name'])

		works[animeUri] = {
			'startYear': startYear, 
			'favorites': favorites, 
			'score': score, 
			'popularity': popularity, 
			'genres': genres
		}
	
	return works

def addNewNodes(G, seiyuusOldWorks, currentYear):
	seiyuuList = getSeiyuusWithDebutIn(currentYear)

	for seiyuu in seiyuuList:
		seiyuuUri = seiyuu['seiyuu_uri']['value']
		seiyuuData = seiyuuCollection.find_one({"id":seiyuuUri})
		
		name = seiyuu['seiyuu_name']['value']
		debut = seiyuu['debut']['value']
		gender = seiyuu['gender']['value']

		birthday = birthplace = 'Null'
		if 'birthday' in seiyuu:
			birthday = seiyuu['birthday']['value']

		if 'birthplace' in seiyuu:
			birthplace = seiyuu['birthplace']['value']

		popularity = seiyuuData['member_favorites']

		# Add new works
		newWorks = getAnimegraphyStartingIn(seiyuuUri, currentYear)
		if seiyuuUri not in seiyuusOldWorks:
			seiyuusOldWorks[seiyuuUri] = {}

		seiyuusOldWorks[seiyuuUri].update(newWorks)

		G.add_node(seiyuuUri, 
			label = name, 
			debut = debut,
			gender = gender,
			birthday = birthday,
			birthplace = birthplace,
			popularity = popularity, 
			works = seiyuusOldWorks[seiyuuUri])

def addNewEdges(G, seiyuusOldWorks, currentYear): 
	for seiyu1 in G.nodes():
		works1 = Set(seiyuusOldWorks[seiyu1].keys())
		
		for seiyu2 in G.nodes():
			works2 = Set(seiyuusOldWorks[seiyu2].keys())
			
			if not G.has_edge(seiyu1, seiyu2):
				worksInCommon = works1.intersection(works2)
				if seiyu1 < seiyu2 and len(worksInCommon) >= requiredWorksInCommon:
					G.add_edge(seiyu1, seiyu2)

def addNewNodesAndEdges(socialNetworkGraph, seiyuusOldWorks, currentYear):
	addNewNodes(socialNetworkGraph, seiyuusOldWorks, currentYear)
	addNewEdges(socialNetworkGraph, seiyuusOldWorks, currentYear)

def main(requiredWorksInCommon, fromYear, toYear):
	xs = xrange(fromYear, toYear+1)
	nodesY = []
	edgesY = []

	socialNetworkGraph = nx.Graph()
	seiyuusOldWorks = {}
	
	startingYear = fromYear
	for currentYear in xrange(fromYear, toYear+1):
		print('working on {0}-{1}'.format(startingYear, currentYear))

		addNewNodesAndEdges(socialNetworkGraph, seiyuusOldWorks, currentYear)

		# SAVE IT
		nx.write_gexf(socialNetworkGraph, "graphs/atLeast{0}Works_{1}-{2}.gexf".format(requiredWorksInCommon, startingYear, currentYear))
		
		# ANALIZE IT
		nodesY.append(nx.number_of_nodes(socialNetworkGraph))
		edgesY.append(nx.number_of_edges(socialNetworkGraph))

	# xs = range(1960, 2019)

	# nodeFilename = 'accumulationNodes_{0}_{1}-{2}'.format(requiredWorksInCommon, fromYear, toYear)
	# with open('aux/{0}.json'.format(nodeFilename), 'w') as nodesOutputFile:
	# 	nodesOutputFile.write(json.dumps({
	# 	'xs': xs, 
	# 	'ys': nodesY, 
	# 	'color': 'r', 
	# 	'xlabel': 'Years', 
	# 	'ylabel': 'Number of nodes', 
	# 	'title': 'Accumulation of nodes over time, with at least {0} works in common'.format(requiredWorksInCommon), 
	# 	'outputFileName': nodeFilename
	# }))
	
	# edgesFilename = 'accumulationEdges_{0}_{1}-{2}.json'.format(requiredWorksInCommon, fromYear, toYear)
	# with open('aux/{0}.json'.format(edgesFilename), 'w') as edgesOutputFile:
	# 	edgesOutputFile.write(json.dumps({
	# 	'xs': xs, 
	# 	'ys': edgesY, 
	# 	'color': 'b', 
	# 	'xlabel': 'Years', 
	# 	'ylabel': 'Number of edges', 
	# 	'title': 'Accumulation of edges over time, with at least {0} works in common'.format(requiredWorksInCommon), 
	# 	'outputFileName': edgesFilename
	# }))

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
