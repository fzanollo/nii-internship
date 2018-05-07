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

def getSeiyuuList(startingYear, endingYear):
	return querySPARQLEndpoint("""
		SELECT ?seiyu_uri ?seiyu_name ?debut
		WHERE {{
			?seiyu_uri wdt:P106 wd:Q622807.
			?seiyu_uri rdfs:label ?seiyu_name.
			?anime_uri wdt:P725 ?seiyu_uri.
			?seiyu_uri wdt:P2031 ?debut.

			filter(?debut >= {0} && ?debut <= {1})
		}} group by ?seiyu_uri
		""".format(startingYear, endingYear))

def getAnimegraphy(seiyuUri, fromYear, toYear):
	animes = querySPARQLEndpoint("""
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
		""".format(seiyuUri, fromYear, toYear))

	works = Set()
	for item in animes:
		works.add((item['anime_uri']['value'], item['start_year']['value']))
	
	return works

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
		debut = seiyuu['debut']['value']
		popularity = seiyuuData['data']['member_favorites']
		works = getAnimegraphy(seiyuUri, fromYear, toYear)

		seiyuuWorksDict[seiyuUri] = works

		G.add_node(seiyuUri, label= name, popularity= popularity, debut= debut)

	# EDGES
	for seiyu1, works1 in seiyuuWorksDict.iteritems():
		for seiyu2, works2 in seiyuuWorksDict.iteritems():
			worksInCommon = works1.intersection(works2)
			if seiyu1 < seiyu2 and len(worksInCommon) >= requiredWorksInCommon: #seiyu1 < seiyu2 para que no haya repetidos (mejorar)
				G.add_edge(seiyu1, seiyu2)

	return G

def main():
	requiredWorksInCommon = 1
	fromYear = 1960
	toYear = 2018
	step = 10

	# print("Make social network graph")
	# requiredWorksInCommon = input("required works in common: ")
	# fromYear = input("from year: ")
	# toYear = input("to year: ")
	# step = input("step: ")

	startingYear = fromYear
	for endingYear in xrange(fromYear, toYear+step, step):
		# endingYear = startingYear + step # mejorar, tiene problema si el step no es divisor del intervalo total 

		print('working on {0}-{1}'.format(startingYear, endingYear))

		seiyuuList = getSeiyuuList(startingYear, endingYear)
		
		# MAKE GRAPH
		G = makeGraph(seiyuuList, startingYear, endingYear, requiredWorksInCommon)
		
		# SAVE IT
		nx.write_gexf(G, "graphs/atLeast{0}Works_{1}-{2}.gexf".format(requiredWorksInCommon, startingYear, endingYear))
		
		# ANALIZE IT
		degree_histogram = nx.degree_histogram(G)
		degree = nx.degree(G)
		btwCentralities = nx.betweenness_centrality(G)
		popularities = nx.get_node_attributes(G, 'popularity')
		debuts = nx.get_node_attributes(G, 'debut')

		# print(degree)
		# 
		xValues = debuts
		yAvg = degree

		intermediateDict = {}
		for node, xValue in xValues.iteritems():

			if xValue not in intermediateDict:
				intermediateDict[xValue] = []
			
			intermediateDict[xValue].append(yAvg[node])

		for xValue, yValues in intermediateDict.iteritems():
			intermediateDict[xValue] = sum(map(lambda y: (y/nx.number_of_nodes(G))*100, yValues)) / len(yValues)

		sortedXYavg = sorted(intermediateDict.items())
		
		xs = [x[0] for x in sortedXYavg]
		ys = [y[1] for y in sortedXYavg]

		# PLOT THE ANALYSIS
		
		fig, ax = plt.subplots()
		ax.plot(xs, ys)
		ax.set_xticks(xs)
		# ax.set_xticklabels([str(x)[-2:] for x in xs])
		# ax.set_title('')
		# ax.set_xlabel('')
		# ax.set_ylabel('')
		plt.savefig('graphics/atLeast{0}Works_{1}-{2}.pdf'.format(requiredWorksInCommon, startingYear, endingYear))
		plt.close()

		# PLOT THE GRAPH (por ahora asi nomas)
		# G.graph['graph']={'rankdir':'TD'}
		# G.graph['node']={'shape':'circle'}
		# G.graph['edges']={'arrowsize':'4.0'}

		# A = to_agraph(G)
		# # print(A)
		# A.layout('dot')
		# A.draw('graphics/abcd.png')
	
	
if __name__ == '__main__':
	main()