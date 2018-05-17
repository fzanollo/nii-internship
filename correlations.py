import sys
from sets import Set
import re

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

def getAmountOfWorksStartingIn(seiyuUri, year):
	result = querySPARQLEndpoint("""
		SELECT count(?anime_uri)
		WHERE {{
			?anime_uri wdt:P725 <{0}>.
			
			?anime_uri wdt:P580 ?start_year.
			FILTER(?start_year >= {1})
		}}
		""".format(seiyuUri, year))

	return int(result[0]['callret-0']['value'])

def getAmountOfWorks(seiyuUri):
	return getAmountOfWorksStartingIn(seiyuUri, 1960)

def plotHeatmap(correlations, filename):
	# plot heatmap
	ax = sns.heatmap(correlations.T, annot=True, cmap="Reds")
	# turn the axis label
	for item in ax.get_xticklabels():
	    item.set_rotation(90)
	# save figure
	plt.savefig('graphics/{0}.png'.format(filename), bbox_inches='tight', dpi=100)
	plt.close()

def plotScatterBetween(dataFrame, xName, yName, pearsonCorrelations, spearmanCorrelations):
	pearsonCorrelation = round(pearsonCorrelations[xName][yName], 2)
	spearmanCorrelation = round(spearmanCorrelations[xName][yName], 2)

	plt.plot(dataFrame[xName], dataFrame[yName], "o", alpha=0.5)

	ax = plt.gca()
	ax.set_ylim(ymin=0)
	ax.set_xlim(xmin=0)

	ax.plot(ax.get_xlim(), ax.get_ylim(), ls="--", c=".3")

	ax.set_ylabel(yName)
	ax.set_xlabel(xName)
	ax.set_title('Pearson: {0}, Spearman: {1}'.format(pearsonCorrelation, spearmanCorrelation))

	plt.savefig('graphics/{2}scatterCorr_{0}_{1}.png'.format(xName, yName, prefix), bbox_inches='tight', dpi=100)
	plt.close()

def main(inputFileName):
	prefix = re.search(r"\d+", inputFileName).group() + 'Works_'
	socialNetworkGraph = nx.read_gexf(inputFileName)

	# inside info
	degree = dict(nx.degree(socialNetworkGraph))
	
	btwC = nx.betweenness_centrality(socialNetworkGraph)

	closeness = nx.closeness_centrality(socialNetworkGraph)

	eigenvector = nx.eigenvector_centrality(socialNetworkGraph)

	# outside info
	debuts = nx.get_node_attributes(socialNetworkGraph, 'debut')
	activityYears = dict([(seiyu, 2018-int(debut)) for seiyu, debut in debuts.items()])

	popularities = nx.get_node_attributes(socialNetworkGraph, 'popularity')

	amountOfWorks = {}
	amountOfRecentWorks = {}
	for seiyuUri in socialNetworkGraph.nodes():
		amountOfWorks[seiyuUri] = getAmountOfWorks(seiyuUri)
		amountOfRecentWorks[seiyuUri] = getAmountOfWorksStartingIn(seiyuUri, 2008)

	# correlations
	columnDataDict = {
		'degree': degree, 
		'betweenness': btwC, 
		'closeness': closeness,
		'eigenvector': eigenvector,
		'activityYears': activityYears,
		'popularity': popularities,
		'amountOfWorks': amountOfWorks,
		'amountOfRecentWorks': amountOfRecentWorks
	}

	df = pd.DataFrame(columnDataDict)

	# Spearman, Pearson, Kendall
	pearsonCorr = df.corr('pearson')
	spearmanCorr = df.corr('spearman')
	kendallCorr = df.corr('kendall')

	plotHeatmap(pearsonCorr, prefix + 'correlation_Pearson')
	plotHeatmap(spearmanCorr, prefix + 'correlation_Spearman')
	plotHeatmap(kendallCorr, prefix + 'correlation_Kendall')

	# plotScatterBetween(df, 'amountOfWorks', 'betweenness', pearsonCorr, spearmanCorr, prefix)
	# plotScatterBetween(df, 'amountOfWorks', 'closeness', pearsonCorr, spearmanCorr, prefix)
	# plotScatterBetween(df, 'amountOfWorks', 'popularity', pearsonCorr, spearmanCorr, prefix)
	# plotScatterBetween(df, 'eigenvector', 'activityYears', pearsonCorr, spearmanCorr, prefix)
	# plotScatterBetween(df, 'popularity', 'activityYears', pearsonCorr, spearmanCorr, prefix)
	# plotScatterBetween(df, 'amountOfWorks', 'activityYears', pearsonCorr, spearmanCorr, prefix)
	# plotScatterBetween(df, 'degree', 'activityYears', pearsonCorr, spearmanCorr, prefix)
	# plotScatterBetween(df, 'degree', 'popularity', pearsonCorr, spearmanCorr, prefix)
	# plotScatterBetween(df, 'amountOfRecentWorks', 'popularity', pearsonCorr, spearmanCorr, prefix)
	

if __name__ == '__main__':
	inputFileName = 'graphs/atLeast1Works_1960-1960.gexf'

	if len(sys.argv) >= 2:
		inputFileName = sys.argv[1]

	main(inputFileName)