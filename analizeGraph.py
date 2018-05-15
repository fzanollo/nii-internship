import sys

from sets import Set

import yaml
import json

from SPARQLWrapper import SPARQLWrapper, JSON

import networkx as nx

def querySPARQLEndpoint(query):
	sparql = SPARQLWrapper("http://localhost:8890/sparql")

	sparql.setQuery(query)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()

	bindings = yaml.load(json.dumps(results["results"]["bindings"]))

	return bindings

def getAnimegraphy(seiyuUri):
	animes = querySPARQLEndpoint("""
		SELECT ?anime_uri
		WHERE {{
			?anime_uri wdt:P725 <{0}>.
		}}
		""".format(seiyuUri))

	works = Set()
	for item in animes:
		works.add(item['anime_uri']['value'])
	
	return works

def outputJsonForGraphic(data, name, outputFileName, popularities=None):
	order = 'desc'
	xyPairs = []

	if popularities != None: #order by popularity
		order = 'by popularity'
		for seiyu, pop in popularities:
			xyPairs.append((seiyu, data[seiyu]))
	else: #order desc
		xyPairs = sorted(data.items(), key=lambda x: x[1], reverse=True)
	
	xs = [x for x, y in xyPairs]
	ys = [y for x, y in xyPairs]

	with open('aux/{0}.json'.format(outputFileName), 'w') as outputFile:
		outputFile.write(json.dumps({
		'xs': xs, 
		'ys': ys, 
		'color': 'r', 
		'xlabel': 'Seiyuu', 
		'ylabel': '{0}'.format(name), 
		'title': '{0} per seiyuu, ordered {1}'.format(name, order), 
		'outputFileName': outputFileName
	}))

def main(inputFileName):
	socialNetworkGraph = nx.read_gexf(inputFileName)

	popularities = nx.get_node_attributes(socialNetworkGraph, 'popularity')
	popularities = sorted(popularities.items(), key=lambda x: x[1], reverse=True)

	btwC = nx.betweenness_centrality(socialNetworkGraph)
	outputJsonForGraphic(btwC, 'Betweenness centrality', 'btwCPerSeiyuu')
	outputJsonForGraphic(btwC, 'Betweenness centrality', 'popularityXbtwC', popularities)

	debuts = nx.get_node_attributes(socialNetworkGraph, 'debut')
	activityYears = dict([(seiyu, 2018-int(debut)) for seiyu, debut in debuts.items()])
	outputJsonForGraphic(activityYears, 'Activity Years', 'activityYearsPerSeiyuu')
	outputJsonForGraphic(activityYears, 'Activity Years', 'popularityXactivityYears', popularities)

	degree = dict(nx.degree(socialNetworkGraph))
	outputJsonForGraphic(degree, 'Degree', 'degreePerSeiyuu')
	outputJsonForGraphic(degree, 'Degree', 'popularityXdegree', popularities)

if __name__ == '__main__':
	inputFileName = 'graphs/atLeast1Works_1960-1960.gexf'

	if len(sys.argv) >= 2:
		inputFileName = sys.argv[1]

	main(inputFileName)