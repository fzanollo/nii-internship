import sys
from sets import Set
import re

import yaml
import json

import networkx as nx
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from SPARQLWrapper import SPARQLWrapper, JSON

from pymongo import MongoClient

client = MongoClient()
db = client.seiyuuData
animeCollection = db.anime
seiyuuCollection = db.seiyuu

def querySPARQLEndpoint(query):
	sparql = SPARQLWrapper("http://localhost:8890/sparql")

	sparql.setQuery(query)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()

	bindings = yaml.load(json.dumps(results["results"]["bindings"]))

	return bindings

def getWorksStartingIn(seiyuuUri, year):
	return querySPARQLEndpoint("""
		SELECT ?anime_uri
		WHERE {{
			?anime_uri wdt:P725 <{0}>.
			
			?anime_uri wdt:P580 ?start_year.
			FILTER(?start_year >= {1})
		}}
		""".format(seiyuuUri, year))

def getAmountOfWorksStartingIn(seiyuuUri, year):
	result = querySPARQLEndpoint("""
		SELECT count(?anime_uri)
		WHERE {{
			?anime_uri wdt:P725 <{0}>.
			
			?anime_uri wdt:P580 ?start_year.
			FILTER(?start_year >= {1})
		}}
		""".format(seiyuuUri, year))

	return int(result[0]['callret-0']['value'])

def getAmountOfWorks(seiyuuUri):
	return getAmountOfWorksStartingIn(seiyuuUri, 1960)

def plotHeatmap(correlations, filename):
	# plot heatmap
	plt.subplots(figsize=(15,10))
	ax = sns.heatmap(correlations.T, annot=True, cmap="Reds")
	# turn the axis label
	for item in ax.get_xticklabels():
	    item.set_rotation(90)
	# save figure
	plt.savefig('graphics/{0}.png'.format(filename), bbox_inches='tight', dpi=100)
	plt.close()

def plotScatterBetween(dataFrame, xName, yName, pearsonCorrelations, spearmanCorrelations, prefix):
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

def measures(values):
	suma = mean = median = maximum = 0
	if len(values)>0:
		suma = sum(values)
		mean = np.mean(values)
		median = np.median(values)
		maximum = max(values)
	# return suma, mean, median, maximum
	return mean

def getMalNumberFromUri(animeUri):
	return int(animeUri[animeUri.rfind('/')+1:])

def isMainRole(seiyuuUri, animeUri):
	res = False
	roleInfo = seiyuuCollection.find_one(
		{"id": "{0}".format(seiyuuUri)}, 
		{"voice_acting_role": {"$elemMatch":{"anime.mal_id":getMalNumberFromUri(animeUri)}}})
	
	if "voice_acting_role" in roleInfo: 
		role = roleInfo["voice_acting_role"][0]['character']['role']		
		res = role == 'Main'

	return res

def attributeOfWorksStartingIn(seiyuuUri, year, attribute):
	works = [elem['anime_uri']['value'] for elem in getWorksStartingIn(seiyuuUri, year)]
	worksInfo = animeCollection.find({"id": {"$in": works}}, {'id':1, attribute:1})

	values = []
	for work in worksInfo:
		value = work[attribute]

		if attribute != 'genre':
			if isMainRole(seiyuuUri, work['id']):
				values.append(value)
			else:
				values.append(value//2)

	return values

def numberOfMainRolesFor(seiyuuUri):
	works = getWorksStartingIn(seiyuuUri, 1960)

	numberOfMainRoles = 0

	values = []
	for work in works:
		animeUri = work['anime_uri']['value']

		if isMainRole(seiyuuUri, animeUri):
			numberOfMainRoles += 1

	if numberOfMainRoles>0:
		print('{0}: {1}'.format(seiyuuUri, numberOfMainRoles))
	return numberOfMainRoles

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
	genders = nx.get_node_attributes(socialNetworkGraph, 'gender')

	#-------
	amountOfWorks = {}
	amountOfRecentWorks = {}
	avgPopularityOfWorks = {}
	avgPopularityOfRecentWorks = {}
	avgScoreOfWorks = {}
	avgScoreOfRecentWorks = {}
	avgMembersOfWorks = {}
	avgMembersOfRecentWorks = {}
	numberOfMainRoles = {}

	for seiyuuUri in socialNetworkGraph.nodes():
		amountOfWorks[seiyuuUri] = getAmountOfWorks(seiyuuUri)
		# amountOfRecentWorks[seiyuuUri] = getAmountOfWorksStartingIn(seiyuuUri, 2009)

		avgPopularityOfWorks[seiyuuUri] = measures(attributeOfWorksStartingIn(seiyuuUri, 1960, 'popularity'))
		# avgPopularityOfRecentWorks[seiyuuUri] = measures(attributeOfWorksStartingIn(seiyuuUri, 2009, 'popularity'))

		avgScoreOfWorks[seiyuuUri] = measures(attributeOfWorksStartingIn(seiyuuUri, 1960, 'score'))
		# avgScoreOfRecentWorks[seiyuuUri] = measures(attributeOfWorksStartingIn(seiyuuUri, 2009, 'score'))

		avgMembersOfWorks[seiyuuUri] = measures(attributeOfWorksStartingIn(seiyuuUri, 1960, 'members'))
		# avgMembersOfRecentWorks[seiyuuUri] = measures(attributeOfWorksStartingIn(seiyuuUri, 2009, 'members'))

		numberOfMainRoles[seiyuuUri] = numberOfMainRolesFor(seiyuuUri)


	# correlations
	columnDataDict = {
		'degree': degree, 
		'betweenness': btwC, 
		'closeness': closeness,
		'eigenvector': eigenvector,

		'debut': debuts,
		'activityYears': activityYears,
		'popularity': popularities,
		
		'amountOfWorks': amountOfWorks,
		# 'amountOfRecentWorks(last9years)': amountOfRecentWorks,

		'avgPopularityOfWorks': avgPopularityOfWorks,
		# 'avgPopularityOfRecentWorks': avgPopularityOfRecentWorks,
		'avgScoreOfWorks': avgScoreOfWorks,
		# 'avgScoreOfRecentWorks': avgScoreOfRecentWorks,
		'avgMembersOfWorks': avgMembersOfWorks,
		# 'avgMembersOfRecentWorks': avgMembersOfRecentWorks,

		'numberOfMainRoles': numberOfMainRoles
	}

	df = pd.DataFrame(columnDataDict)

	# Spearman, Pearson, Kendall
	pearsonCorr = df.corr('pearson')
	# print(pearsonCorr)
	# spearmanCorr = df.corr('spearman')
	# kendallCorr = df.corr('kendall')

	plotHeatmap(pearsonCorr, prefix + 'correlation_Pearson')
	# plotHeatmap(spearmanCorr, prefix + 'correlation_Spearman')
	# plotHeatmap(kendallCorr, prefix + 'correlation_Kendall')

	# plotScatterBetween(df, 'amountOfWorks', 'betweenness', pearsonCorr, spearmanCorr, prefix)

	
	

if __name__ == '__main__':
	inputFileName = 'graphs/atLeast1Works_1960-1960.gexf'

	if len(sys.argv) >= 2:
		inputFileName = sys.argv[1]

	main(inputFileName)