import sys
import io

import yaml
import json

from pymongo import MongoClient

def outputPrefixes():
	prefixes = [('rdfs', 'http://www.w3.org/2000/01/rdf-schema#'), ('wdt', 'http://www.wikidata.org/prop/direct/'), ('wd','http://www.wikidata.org/entity/')]
	prefixesForOutput = u''

	for prefix in prefixes:
		prefixesForOutput += u'@prefix {0}: <{1}> .\n'.format(prefix[0], prefix[1])

	prefixesForOutput += u'\n'
	return prefixesForOutput

def getStartAndEndingYearFromAiredString(airedString):
	startYear = endYear = None

	if airedString != "Not available":
		toIndex = airedString.find('to')

		if toIndex == -1:
			startYear = int(airedString[-4:])
		else:
			startYear = int(airedString[toIndex-5:toIndex-1])

			if '?' not in airedString:
				endYear = int(airedString[-4:])

	return startYear, endYear

def getStartAndEndingYear(animeData):
	startYear = animeData['aired']['from']
	endYear = animeData['aired']['to']

	if startYear == None:
		startYear, end = getStartAndEndingYearFromAiredString(animeData['aired_string'])
	else:
		startYear = int(animeData['aired']['from'][:4])

	if endYear == None:
		start, endYear = getStartAndEndingYearFromAiredString(animeData['aired_string'])
	else:
		endYear = int(animeData['aired']['to'][:4])

	return startYear, endYear

def main(inputFileName, outputFileName):
	animeUris = yaml.load(io.open(inputFileName, 'r', encoding="utf-8"))

	outputFile = io.open(outputFileName, 'w', encoding="utf-8")
	outputFile.write(outputPrefixes())

	client = MongoClient()
	db = client.seiyuuData
	animeCollection = db.anime

	for anime in animeUris:
		animeUri = anime['anime_uri']['value']
		animeData = animeCollection.find_one({"id":animeUri})

		startYear, endYear = getStartAndEndingYear(animeData)

		# anime_uri wdt:instance_of wd:anime 
		outputFile.write(u'<{0}> {1} {2} .\n'.format(animeUri, 'wdt:P31', 'wd:Q1107'))

		if startYear != None:
			# anime_uri wdt:start_time point_in_time
			outputFile.write(u'<{0}> {1} {2} .\n'.format(animeUri, 'wdt:P580', startYear))

		if endYear != None:
			# anime_uri wdt:end_time point_in_time
			outputFile.write(u'<{0}> {1} {2} .\n'.format(animeUri, 'wdt:P582', endYear))

if __name__ == '__main__':
	inputFileName = 'output.json'
	outputFileName = 'output.ttl'

	if len(sys.argv) >= 3:
		inputFileName = sys.argv[1]
		outputFileName = sys.argv[2] + '.ttl'

	main(inputFileName, outputFileName)