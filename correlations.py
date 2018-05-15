import sys
from sets import Set

import yaml
import json

import networkx as nx
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from SPARQLWrapper import SPARQLWrapper, JSON

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

def main(inputFileName):
	socialNetworkGraph = nx.read_gexf(inputFileName)

	# inside info
	degree = dict(nx.degree(socialNetworkGraph))
	
	btwC = nx.betweenness_centrality(socialNetworkGraph)

	closseness = nx.closeness_centrality(socialNetworkGraph)

	eigenvector = nx.eigenvector_centrality(socialNetworkGraph)

	# outside info
	debuts = nx.get_node_attributes(socialNetworkGraph, 'debut')
	activityYears = dict([(seiyu, 2018-int(debut)) for seiyu, debut in debuts.items()])

	popularities = nx.get_node_attributes(socialNetworkGraph, 'popularity')

	amountOfWorks = {}
	for seiyuUri in socialNetworkGraph.nodes():
		amountOfWorks[seiyuUri] = len(getAnimegraphy(seiyuUri))

	# correlations
	columnDataDict = {
		'degree': degree, 
		'betweenness': btwC, 
		'closseness': closseness,
		'eigenvector': eigenvector,
		'activityYears': activityYears,
		'popularity': popularities,
		'amountOfWorks': amountOfWorks
	}

	df = pd.DataFrame(columnDataDict)
	correlations = df.corr()

	# plot heatmap

	ax = sns.heatmap(correlations.T, annot=True, cmap="Reds")

	# turn the axis label
	for item in ax.get_xticklabels():
	    item.set_rotation(90)

	# save figure
	plt.savefig('seabornPandas.png', bbox_inches='tight', dpi=100)
	plt.show()

if __name__ == '__main__':
	inputFileName = 'graphs/atLeast1Works_1960-1960.gexf'

	if len(sys.argv) >= 2:
		inputFileName = sys.argv[1]

	main(inputFileName)