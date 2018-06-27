import sys
from datetime import date
from itertools import combinations
from collections import OrderedDict
import operator

import yaml
import json

import networkx as nx
import pandas as pd
import numpy as np

# ---
from sklearn.tree import DecisionTreeRegressor
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LinearRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.naive_bayes import GaussianNB
from sklearn.svm import SVC
# ---

from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split, KFold, cross_val_score
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
	rawWorkData = querySPARQLEndpoint("""
		SELECT ?anime_uri
		WHERE {{
			?anime_uri wdt:P725 <{0}>.
			
			?anime_uri wdt:P580 ?start_year.
			FILTER(?start_year >= {1})
		}}
		""".format(seiyuuUri, year))
	works = [w['anime_uri']['value'] for w in rawWorkData]
	return works

def measures(values):
	suma = mean = median = maximum = 0
	if len(values)>0:
		suma = sum(values)
		mean = np.mean(values)
		median = np.median(values)
		maximum = max(values)
	return suma, mean, median, maximum

def attributeOfWorksStartingIn(seiyuuUri, year, attribute):
	works = getWorksStartingIn(seiyuuUri, year)
	worksInfo = animeCollection.find({"id": {"$in": works}}, {'id':1, attribute:1})

	values = [ws[attribute] for ws in worksInfo]

	return values

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

def plotPredictions(measured, predicted, filename, boundaries):
	measured = measured['popularity'].tolist()
	predicted = predicted.tolist()

	fig, ax = plt.subplots()
	ax.scatter(measured, predicted, edgecolors=(0, 0, 0))
	ax.plot(boundaries, boundaries, 'k--', lw=4)
	ax.set_xlabel('Measured')
	ax.set_ylabel('Predicted')

	plt.title(filename)
	plt.savefig('cart/predictions/{0}.png'.format(filename), bbox_inches='tight', dpi=100)
	# plt.show()
	plt.close()

	with open('cart/predictions/{0}.json'.format(filename), 'w') as outputFile:
		outputFile.write(json.dumps({
			'xs': measured,
			'ys': predicted,
			'color': 'r', 
			'xlabel': 'Measured', 
			'ylabel': 'Predicted', 
			'title': filename,
			'outputFileName': filename,
			'boundaries': [int(x) for x in boundaries]
		}))

def plotTree(model, data, filename):
	dot_data = StringIO()

	export_graphviz(model, out_file=dot_data,  
	                filled=True, rounded=True,
	                special_characters=True, feature_names=data.columns.values.tolist())

	graph = pydotplus.graph_from_dot_data(dot_data.getvalue())  
	graph.write_png('cart/tree/{0}.png'.format(filename))

def preparePersonalData(socialNetworkGraph):
	debuts = nx.get_node_attributes(socialNetworkGraph, 'debut')
	genders = nx.get_node_attributes(socialNetworkGraph, 'gender')
	activityYears = dict([(seiyu, 2018-int(debut)) for seiyu, debut in debuts.items()])

	# TODO: next code can work in an unexpected way since dictionaries are not ordered
	genderEncoder = LabelEncoder().fit(genders.values())
	genders = dict(zip(genders.keys(), genderEncoder.transform(genders.values()))) 

	personalData = pd.DataFrame(debuts, index=['debut']).T
	personalData['gender'] = pd.Series(genders, index=personalData.index)
	personalData['activityYears'] = pd.Series(activityYears, index=personalData.index)

	return personalData

def prepareGraphData(socialNetworkGraph):
	degree = dict(nx.degree(socialNetworkGraph))
	btwC = nx.betweenness_centrality(socialNetworkGraph)
	closeness = nx.closeness_centrality(socialNetworkGraph)
	eigenvector = nx.eigenvector_centrality(socialNetworkGraph)

	graphData = pd.DataFrame(degree, index=['degree']).T
	graphData['btwC'] = pd.Series(btwC, index=graphData.index)
	graphData['closeness'] = pd.Series(closeness, index=graphData.index)
	graphData['eigenvector'] = pd.Series(eigenvector, index=graphData.index)
	
	return graphData

def getTop5Genres(worksGenreList):
	genreAmountDict = {}

	for workGenre in worksGenreList:
		for genre in workGenre:
			genre = genre['name']
			if genre not in genreAmountDict:
				genreAmountDict[genre] = 0
			genreAmountDict[genre] += 1

	allGenres = [x[0] for x in sorted(genreAmountDict.items(), key=operator.itemgetter(1), reverse=True)]
	top5Genres = allGenres[:5]

	if len(top5Genres) < 5:
		top5Genres += [u'None' for x in xrange(5-len(top5Genres))]

	return top5Genres

def prepareWorkAndRecentWorkData(socialNetworkGraph):
	workDataPerSeiyuu = {}
	recentWorkDataPerSeiyuu = {}
	
	desiredFeaturesOfWorks = ['favorites', 'score', 'popularity']

	allGenres = [u'Police', u'Sci-Fi', u'Space', u'Vampire', u'Demons', u'Sports', u'Romance', u'Supernatural', 
		u'Comedy', u'Yaoi', u'Harem', u'Josei', u'Mecha', u'Slice of Life', u'Cars', u'Horror', u'Game', u'Shoujo', 
		u'Adventure', u'Shounen Ai', u'Ecchi', u'Thriller', u'Yuri', u'Mystery', u'School', u'Kids', u'Magic', u'Drama', 
		u'Samurai', u'Historical', u'Action', u'Military', u'Parody', u'Seinen', u'Dementia', u'Shounen', u'Psychological', 
		u'Fantasy', u'Music', u'Hentai', u'Martial Arts', u'Super Power', u'Shoujo Ai', u'None']
	genreEncoder = LabelEncoder().fit(allGenres)

	for seiyuuUri in socialNetworkGraph.nodes():
		workData = {}
		recentWorkData = {}

		# amount
		workData['amountOfWorks'] = amountOfWorksFor(seiyuuUri)
		recentWorkData['amountOfRecentWorks'] = amountOfWorksForStartingIn(seiyuuUri, 2009)

		# genre
		top5Genres = getTop5Genres(attributeOfWorksStartingIn(seiyuuUri, 1960, 'genre'))
		workData['worksGenre1'] = genreEncoder.transform([top5Genres[0]])
		workData['worksGenre2'] = genreEncoder.transform([top5Genres[1]])
		workData['worksGenre3'] = genreEncoder.transform([top5Genres[2]])
		workData['worksGenre4'] = genreEncoder.transform([top5Genres[3]])
		workData['worksGenre5'] = genreEncoder.transform([top5Genres[4]])

		top5Genres = getTop5Genres(attributeOfWorksStartingIn(seiyuuUri, 2009, 'genre'))
		recentWorkData['recentWorksGenre1'] = genreEncoder.transform([top5Genres[0]])
		recentWorkData['recentWorksGenre2'] = genreEncoder.transform([top5Genres[1]])
		recentWorkData['recentWorksGenre3'] = genreEncoder.transform([top5Genres[2]])
		recentWorkData['recentWorksGenre4'] = genreEncoder.transform([top5Genres[3]])
		recentWorkData['recentWorksGenre5'] = genreEncoder.transform([top5Genres[4]])

		# other features
		for feature in desiredFeaturesOfWorks:
			suma, mean, median, maximum = measures(attributeOfWorksStartingIn(seiyuuUri, 1960, feature))
			workData[feature + 'OfWorks_Sum'] = suma
			workData[feature + 'OfWorks_Mean'] = mean
			workData[feature + 'OfWorks_Median'] = median
			workData[feature + 'OfWorks_Max'] = maximum
			
			suma, mean, median, maximum = measures(attributeOfWorksStartingIn(seiyuuUri, 2009, feature))
			recentWorkData[feature + 'OfRecentWorks_Sum'] = suma
			recentWorkData[feature + 'OfRecentWorks_Mean'] = mean
			recentWorkData[feature + 'OfRecentWorks_Median'] = median
			recentWorkData[feature + 'OfRecentWorks_Max'] = maximum

		workDataPerSeiyuu[seiyuuUri] = workData
		recentWorkDataPerSeiyuu[seiyuuUri] = recentWorkData

	workData = pd.DataFrame(workDataPerSeiyuu).T
	recentWorkData = pd.DataFrame(recentWorkDataPerSeiyuu).T
	
	return workData, recentWorkData

def runModels(models, data, target, categoryName):
	results = {}

	data_train, data_test, target_train, target_test = train_test_split(data, target, test_size=0.20)
	for modelName, model in models.iteritems():
		model.fit(data_train, target_train)

		predicted = model.predict(data_test)

		plotPredictions(target_test, predicted, categoryName + '_' + modelName, [target.min(), target.max()])

		results[modelName] = round(metrics.r2_score(target_test, predicted), 2)
		

		if modelName == 'DecisionTreeClassifier':
			featureImportances = pd.Series(model.feature_importances_, index=data.columns)
			featureImportances = featureImportances.nlargest(20)
			featureImportances.plot(kind='barh')
			plt.title(categoryName)
			plt.savefig('cart/tree/{0}_DTC_featureImportances.png'.format(categoryName), bbox_inches='tight', dpi=100)
			# plt.show()
			plt.close()

	return results

def main(inputFileName):
	socialNetworkGraph = nx.read_gexf(inputFileName)

	# DATA CATEGORIES
	personalData = preparePersonalData(socialNetworkGraph)
	graphData = prepareGraphData(socialNetworkGraph)
	workData, recentWorkData = prepareWorkAndRecentWorkData(socialNetworkGraph)
	
	# TARGET
	popularities = nx.get_node_attributes(socialNetworkGraph, 'popularity')
	popularityData = pd.DataFrame(popularities, index=['popularity']).T

	# # FILTER "OUTLIERS"
	# outliers = filter(lambda k: popularities[k]>1000, popularities)
	# outliers += filter(lambda k: popularities[k]<5, popularities)

	# personalData = personalData.drop(outliers)
	# graphData = graphData.drop(outliers)
	# workData = workData.drop(outliers)
	# recentWorkData = recentWorkData.drop(outliers)
	# popularityData = popularityData.drop(outliers)

	# MODELS
	allCategoriesData = {
		'personalData': personalData, 
		'workData': workData,
		'recentWorkData': recentWorkData,
		'graphData': graphData
	}
	categories = allCategoriesData.keys()

	models = {
		'DecisionTreeRegressor': DecisionTreeRegressor(),
		'DecisionTreeClassifier': DecisionTreeClassifier(),
		'LinearRegression': LinearRegression(),
		'KNeighborsClassifier': KNeighborsClassifier(),
		'LinearDiscriminantAnalysis': LinearDiscriminantAnalysis(),
		'GaussianNB': GaussianNB(),
		'SVM': SVC()
	}

	results = OrderedDict()

	target = popularityData

	for r in xrange(1,len(categories)+1):
		combs = combinations(categories, r)

		for combination in combs:
			categoryName = '_'.join(combination)
			if r == len(categories):
				categoryName = 'AllFeatures'

			print('**************************\n' + categoryName)

			data = pd.concat([allCategoriesData[c] for c in combination], axis=1)
			results[categoryName] = runModels(models, data, target, categoryName)

	with open('cart/predictionR2Score.csv', 'w') as outputFile:
		# TODO: formatear el output para tabla en pdf o algo asi (o seaborn)
		resultsDF = pd.DataFrame(results)
		outputFile.write(resultsDF.to_csv())

if __name__ == '__main__':
	inputFileName = 'graphs/atLeast1Works_1960-1960.gexf'

	if len(sys.argv) >= 2:
		inputFileName = sys.argv[1]

	main(inputFileName)