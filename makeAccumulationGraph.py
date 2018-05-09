import sys
import io
from sets import Set

import yaml
import json

from SPARQLWrapper import SPARQLWrapper, JSON
from pymongo import MongoClient

import networkx as nx
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from networkx.drawing.nx_agraph import graphviz_layout, to_agraph

client = MongoClient()
db = client.seiyuuData
seiyuuCompleteData = db.seiyuu

def querySPARQLEndpoint(query):
	sparql = SPARQLWrapper("http://localhost:8890/sparql")

	sparql.setQuery(query)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()

	bindings = yaml.load(json.dumps(results["results"]["bindings"]))

	return bindings

def getSeiyuusWithDebutIn(year):
	return querySPARQLEndpoint("""
		SELECT ?seiyu_uri ?seiyu_name ?debut
		WHERE {{
			?seiyu_uri wdt:P106 wd:Q622807.
			?seiyu_uri rdfs:label ?seiyu_name.
			?anime_uri wdt:P725 ?seiyu_uri.
			?seiyu_uri wdt:P2031 ?debut.

			filter(?debut = {0})
		}} group by ?seiyu_uri
		""".format(year))

def getAnimegraphyStartingIn(seiyuUri, year):
	animes = querySPARQLEndpoint("""
		SELECT ?anime_uri ?start_year
		WHERE {{
			?anime_uri wdt:P725 <{0}>.
			
			?anime_uri wdt:P580 ?start_year.
			FILTER(?start_year >= {1})
		}}
		""".format(seiyuUri, year))

	works = Set()
	for item in animes:
		works.add((item['anime_uri']['value'], item['start_year']['value']))
	
	return works

def addNewNodes(G, seiyuuWorksDict, currentYear):
	seiyuuList = getSeiyuusWithDebutIn(currentYear)

	for seiyuu in seiyuuList:
		seiyuUri = seiyuu['seiyu_uri']['value']
		seiyuuData = seiyuuCompleteData.find_one({"id":seiyuUri})
		
		name = seiyuu['seiyu_name']['value']
		popularity = seiyuuData['data']['member_favorites']
		debut = seiyuu['debut']['value']

		G.add_node(seiyuUri, label= name, popularity= popularity, debut= debut)

		# Add new works
		works = getAnimegraphyStartingIn(seiyuUri, currentYear)
		if seiyuUri not in seiyuuWorksDict:
			seiyuuWorksDict[seiyuUri] = set()

		seiyuuWorksDict[seiyuUri].update(works)

def addNewEdges(G, seiyuuWorksDict, currentYear): 
	for seiyu1 in G.nodes():
		works1 = seiyuuWorksDict[seiyu1]
		
		for seiyu2 in G.nodes():
			works2 = seiyuuWorksDict[seiyu2]
			
			if not G.has_edge(seiyu1, seiyu2):
				worksInCommon = works1.intersection(works2)
				if seiyu1 < seiyu2 and len(worksInCommon) >= requiredWorksInCommon:
					G.add_edge(seiyu1, seiyu2)

def addNewNodesAndEdges(socialNetworkGraph, seiyuuWorksDict, currentYear):
	addNewNodes(socialNetworkGraph, seiyuuWorksDict, currentYear)
	addNewEdges(socialNetworkGraph, seiyuuWorksDict, currentYear)

def main(requiredWorksInCommon, fromYear, toYear):
	xs = xrange(fromYear, toYear+1)
	nodesY = []
	edgesY = []

	socialNetworkGraph = nx.Graph()
	seiyuuWorksDict = {}
	
	startingYear = fromYear
	for currentYear in xrange(fromYear, toYear+1):
		print('working on {0}-{1}'.format(startingYear, currentYear))

		addNewNodesAndEdges(socialNetworkGraph, seiyuuWorksDict, currentYear)

		# SAVE IT
		nx.write_gexf(socialNetworkGraph, "graphs/atLeast{0}Works_{1}-{2}.gexf".format(requiredWorksInCommon, startingYear, currentYear))
		
		# ANALIZE IT
		nodesY.append(nx.number_of_nodes(socialNetworkGraph))
		edgesY.append(nx.number_of_edges(socialNetworkGraph))


	# PLOT THE ANALYSIS	
	plt.figure()

	plt.plot(xs,nodesY,'ro-') 
	plt.plot(xs,edgesY,'bv-') 

	# plt.xticks(xs)
	ax = plt.gca()
	ax.yaxis.set_major_locator(MaxNLocator(integer=True))
	ax.yaxis.grid(which="major", color='k', linestyle='-', linewidth=.2)
	
	plt.legend(['Nodes','Edges'])
	plt.xlabel('Years')
	plt.ylabel('Quantity')
	plt.title('Accumulation of nodes and edges over time')
	plt.show()
	plt.savefig('graphics/atLeast{0}Works_{1}-{2}.pdf'.format(requiredWorksInCommon, fromYear, toYear))

	plt.close()
	
	# fig, ax = plt.subplots()
	# ax.plot(xs, ys)
	# ax.set_xticks(xs)
	# ax.set_xticklabels([str(x)[-2:] for x in xs])
	# ax.set_title('')
	# ax.set_xlabel('')
	# ax.set_ylabel('')

if __name__ == '__main__':
	requiredWorksInCommon = 1
	fromYear = 1960
	toYear = 2018

	if len(sys.argv) >= 4:
		requiredWorksInCommon = int(sys.argv[1])
		fromYear = int(sys.argv[2])
		toYear = int(sys.argv[3])

	main(requiredWorksInCommon, fromYear, toYear)
