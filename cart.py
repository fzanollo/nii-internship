import sys
import re

import yaml
import json

import networkx as nx
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeRegressor
from sklearn.tree import DecisionTreeClassifier
from sklearn import metrics
from sklearn.externals.six import StringIO  
from IPython.display import Image  
from sklearn.tree import export_graphviz
import pydotplus

import matplotlib.pyplot as plt

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

def measures(values):
	suma = mean = median = maximum = 0
	if len(values)>0:
		suma = sum(values)
		mean = np.mean(values)
		median = np.median(values)
		maximum = max(values)
	return suma, mean, median, maximum

def featureOfWorksStartingIn(seiyuuUri, year, info):
	works = getWorksStartingIn(seiyuuUri, year)
	worksInfo = animeCollection.find({"id": {"$in": works}}, {'id':1, info:1})

	values = [ws[info] for ws in worksInfo]

	return measures(values)

def amountOfWorksForStartingIn(seiyuuUri, year):
	result = querySPARQLEndpoint("""
		SELECT count(?anime_uri)
		WHERE {{
			?anime_uri wdt:P725 <{0}>.
			
			?anime_uri wdt:P580 ?start_year.
			FILTER(?start_year >= {1})
		}}
		""".format(seiyuuUri, year))

	return int(result[0]['callret-0']['value'])

def amountOfWorksFor(seiyuuUri):
	return amountOfWorksForStartingIn(seiyuuUri, 1960)

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

	#-------
	personalDataPerSeiyuu = {}
	workDataPerSeiyuu = {}
	recentWorkDataPerSeiyuu = {}
	graphDataPerSeiyuu = {}

	desiredFeaturesOfWorks = ['favorites', 'score']

	for seiyuuUri in socialNetworkGraph.nodes():
		# PERSONAL -TODO
		personalData = {}
		personalData['activityYears'] = activityYears[seiyuuUri]

		personalDataPerSeiyuu[seiyuuUri] = personalData

		# WORK
		workData = {}
		recentWorkData = {}

		workData['amountOfWorks'] = amountOfWorksFor(seiyuuUri)
		recentWorkData['amountOfWorks'] = amountOfWorksForStartingIn(seiyuuUri, 2009)

		for feature in desiredFeaturesOfWorks:
			suma, mean, median, maximum = featureOfWorksStartingIn(seiyuuUri, 1960, feature)
			workData[feature + 'OfWorks_Sum'] = suma
			workData[feature + 'OfWorks_Mean'] = mean
			workData[feature + 'OfWorks_Median'] = median
			workData[feature + 'OfWorks_Max'] = maximum
			
			suma, mean, median, maximum = featureOfWorksStartingIn(seiyuuUri, 2009, feature)
			recentWorkData[feature + 'OfWorks_Sum'] = suma
			recentWorkData[feature + 'OfWorks_Mean'] = mean
			recentWorkData[feature + 'OfWorks_Median'] = median
			recentWorkData[feature + 'OfWorks_Max'] = maximum

		workDataPerSeiyuu[seiyuuUri] = workData
		recentWorkDataPerSeiyuu[seiyuuUri] = recentWorkData

		# GRAPH -TODO
		graphData = {}
		graphData['degree'] = degree[seiyuuUri]
		graphData['betweenness'] = btwC[seiyuuUri]
		graphData['closeness'] = closeness[seiyuuUri]
		graphData['eigenvector'] = eigenvector[seiyuuUri]

		graphDataPerSeiyuu[seiyuuUri] = graphData

	# DATA FRAMES
	personalDataFrame = pd.DataFrame(personalDataPerSeiyuu)
	workDataFrame = pd.DataFrame(workDataPerSeiyuu)
	recentWorkDataFrame = pd.DataFrame(recentWorkDataPerSeiyuu)
	graphDataFrame = pd.DataFrame(graphDataPerSeiyuu)

	popularityDataFrame = pd.DataFrame(popularities, index=['popularity'])

	# DATA AND TARGET
	data = workDataFrame.T
	target = popularityDataFrame.T

	# ********************** DECISION TREE REGRESSOR ********************** 
	X_train, X_test, y_train, y_test = train_test_split(data, target, test_size=0.20)  

	# instantiate and train it
	regressor = DecisionTreeRegressor()  
	regressor.fit(X_train, y_train)

	# test predictions
	predicted = regressor.predict(X_test)  

	fig, ax = plt.subplots()
	ax.scatter(y_test, predicted, edgecolors=(0, 0, 0))
	ax.plot([target.min(), target.max()], [target.min(), target.max()], 'k--', lw=4)
	ax.set_xlabel('Measured')
	ax.set_ylabel('Predicted')

	plt.savefig('graphics/decisionTreeRegressor.png', bbox_inches='tight', dpi=100)
	# plt.show()
	plt.close()

	# ********************** DECISION TREE CLASSIFIER ********************** 

	# INSTANTIATE AND TRAIN
	model=DecisionTreeClassifier()
	model.fit(data,target)

	# OUTPUT GRAPHIC REPRESENTATION
	dot_data = StringIO()

	export_graphviz(model, out_file=dot_data,  
	                filled=True, rounded=True,
	                special_characters=True, feature_names=data.columns.values.tolist())

	graph = pydotplus.graph_from_dot_data(dot_data.getvalue())  
	graph.write_png('sarasa.png')

	# MAKE PREDICTIONS
	predicted = model.predict(data)

	fig, ax = plt.subplots()
	ax.scatter(target, predicted, edgecolors=(0, 0, 0))
	ax.plot([target.min(), target.max()], [target.min(), target.max()], 'k--', lw=4)
	ax.set_xlabel('Measured')
	ax.set_ylabel('Predicted')

	plt.savefig('graphics/DecisionTreeClassifier.png', bbox_inches='tight', dpi=100)
	# plt.show()
	plt.close()

	# To evaluate performance of the regression algorithm, the commonly used metrics are mean absolute error, mean squared error, and root mean squared error. 
	print('Mean Absolute Error:', metrics.mean_absolute_error(target, predicted))  
	print('Mean Squared Error:', metrics.mean_squared_error(target, predicted))  
	print('Root Mean Squared Error:', np.sqrt(metrics.mean_squared_error(target, predicted))) 

if __name__ == '__main__':
	inputFileName = 'graphs/atLeast1Works_1960-1960.gexf'

	if len(sys.argv) >= 2:
		inputFileName = sys.argv[1]

	main(inputFileName)