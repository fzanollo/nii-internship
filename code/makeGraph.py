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
		SELECT ?seiyuu_uri ?seiyuu_name ?debut ?gender ?birthday ?birthplace
		WHERE {{
			?seiyuu_uri wdt:P106 wd:Q622807.
			?seiyuu_uri rdfs:label ?seiyuu_name.			
			?seiyuu_uri wdt:P2031 ?debut.
			?seiyuu_uri wdt:P21 ?gender.

			optional{{?seiyuu_uri wdt:P569 ?birthday.}}
			optional{{?seiyuu_uri wdt:P19 ?birthplace.}}

			filter(?debut >= {0} && ?debut <= {1})
		}} group by ?seiyuu_uri
		""".format(fromYear, toYear))

def getAnimegraphy(seiyuuUri, fromYear, toYear, animeCollection):
	animes = querySPARQLEndpoint("""
		SELECT ?anime_uri ?start_year
		WHERE {{
			?anime_uri wdt:P725 <{0}>.
			
			?anime_uri wdt:P580 ?start_year.
			FILTER(?start_year >= {1})
		}}
		""".format(seiyuuUri, fromYear))

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

def makeGraph(seiyuuList, fromYear, toYear, requiredWorksInCommon):
	client = MongoClient()
	db = client.seiyuuData
	seiyuuCollection = db.seiyuu
	animeCollection = db.anime

	G = nx.Graph()
	
	seiyuuWorksDict = {}

	# NODES
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
		works = getAnimegraphy(seiyuuUri, fromYear, toYear, animeCollection)

		seiyuuWorksDict[seiyuuUri] = Set(works.keys())

		G.add_node(seiyuuUri, 
			label = name, 
			debut = debut,
			gender = gender,
			birthday = birthday,
			birthplace = birthplace,
			popularity = popularity, 
			works = works)

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
	nx.write_gexf(G, "graphs/atLeast{0}Works_{1}-{2}.gexf".format(requiredWorksInCommon, fromYear, toYear))
	
	
if __name__ == '__main__':
	requiredWorksInCommon = 1
	fromYear = 1960
	toYear = 2018

	if len(sys.argv) >= 4:
		requiredWorksInCommon = int(sys.argv[1])
		toYear = int(sys.argv[3])
		fromYear = int(sys.argv[2])
		
		main(requiredWorksInCommon, fromYear, toYear)
	else:
		print('order of parameters is: requiredWorksInCommon, fromYear, toYear')