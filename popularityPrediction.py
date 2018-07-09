import sys
import os
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
	works = getWorksStartingIn(seiyuuUri, year)
	worksInfo = animeCollection.find({"id": {"$in": works}}, {'id':1, attribute:1})

	values = []
	for work in worksInfo:
		value = work[attribute]

		if attribute != 'genre':
			values.append(value)
			
	return values

def numberOfMainRolesForFrom(seiyuuUri, year):
	works = getWorksStartingIn(seiyuuUri, year)

	numberOfMainRoles = 0

	values = []
	for animeUri in works:
		if isMainRole(seiyuuUri, animeUri):
			numberOfMainRoles += 1

	return numberOfMainRoles

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

def abreviate(columnNames):
	newColumnNames = []

	for coln in columnNames:
		words = coln.split('_')
		newColn = ''
		for word in words:
			letter = word[0]
			newColn = newColn + '+' + letter

		newColumnNames.append(newColn[1:])

	return newColumnNames

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

def prepareWorkAndRecentWorkData(socialNetworkGraph):
	workDataPerSeiyuu = {}
	recentWorkDataPerSeiyuu = {}
	
	desiredFeaturesOfWorks = ['favorites', 'score', 'popularity', 'members']

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

		# number of main roles
		workData['numberOfMainRoles'] = numberOfMainRolesForFrom(seiyuuUri, 1960)
		recentWorkData['numberOfRecentMainRoles'] = numberOfMainRolesForFrom(seiyuuUri, 2009)

		# genre
		top5GenresEncoded = genreEncoder.transform(getTop5Genres(attributeOfWorksStartingIn(seiyuuUri, 1960, 'genre')))
		workData['worksGenre1'] = top5GenresEncoded[0]
		workData['worksGenre2'] = top5GenresEncoded[1]
		workData['worksGenre3'] = top5GenresEncoded[2]
		workData['worksGenre4'] = top5GenresEncoded[3]
		workData['worksGenre5'] = top5GenresEncoded[4]

		top5GenresEncoded = genreEncoder.transform(getTop5Genres(attributeOfWorksStartingIn(seiyuuUri, 2009, 'genre')))
		recentWorkData['recentWorksGenre1'] = top5GenresEncoded[0]
		recentWorkData['recentWorksGenre2'] = top5GenresEncoded[1]
		recentWorkData['recentWorksGenre3'] = top5GenresEncoded[2]
		recentWorkData['recentWorksGenre4'] = top5GenresEncoded[3]
		recentWorkData['recentWorksGenre5'] = top5GenresEncoded[4]

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
		'Personal': personalData, 
		'Work': workData,
		'RecentWorks': recentWorkData,
		'Graph': graphData
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

	# OUTPUT
	resultsDF = pd.DataFrame(results)
	with open('cart/predictionsR2Scores.tex', 'w') as outfile:
		outfile.write(resultsDF.to_csv())

	# one category
	with open('cart/oneCategory_r2score.tex', 'w') as oneCategoryOutfile:
		oneCategoryOutfile.write(resultsDF.ix[:, :4].to_latex()) # first 4 columns

	# two categories
	with open('cart/twoCategories_r2score.tex', 'w') as twoCategoriesOutfile:
		twoCategoriesResults = resultsDF.ix[:, 4:10] # from column 5 to 10
		twoCategoriesResults.columns = abreviate(twoCategoriesResults.columns)

		twoCategoriesOutfile.write(twoCategoriesResults.to_latex())
	
	# three categories
	with open('cart/threeCategories_r2score.tex', 'w') as threeCategoriesOutfile:
		threeCategoriesResults = resultsDF.ix[:, 10:14] # from column 10 to 14
		threeCategoriesResults.columns = abreviate(threeCategoriesResults.columns)

		threeCategoriesOutfile.write(threeCategoriesResults.to_latex())

	# all categories
	with open('cart/allCategories_r2score.tex', 'w') as allCategoriesOutfile:
		allCategoriesOutfile.write(resultsDF.ix[:, 14:15].to_latex()) # last column

if __name__ == '__main__':
	inputFileName = 'graphs/atLeast1Works_1960-1960.gexf'

	if len(sys.argv) >= 2:
		inputFileName = sys.argv[1]

	if not os.path.exists('cart/'):
		os.makedirs('cart/')

	if not os.path.exists('cart/predictions'):
		os.makedirs('cart/predictions')

	if not os.path.exists('cart/tree'):
		os.makedirs('cart/tree')

	main(inputFileName)