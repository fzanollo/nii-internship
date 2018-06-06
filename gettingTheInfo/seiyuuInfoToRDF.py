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

def main(inputFileName, outputFileName):
	seiyuus = yaml.load(io.open(inputFileName, 'r', encoding="utf-8"))

	outputFile = io.open(outputFileName, 'w', encoding="utf-8")
	outputFile.write(outputPrefixes())

	client = MongoClient()
	db = client.seiyuuData
	seiyuuCollection = db.seiyuu

	for seiyuu in seiyuus:
		seiyuuUri = seiyuu['seiyu_uri']['value']
		seiyuuData = seiyuuCollection.find_one({"id":seiyuuUri})

		# seiyu_uri wdt:instance_of wd:human
		outputFile.write(u'<{0}> {1} {2} .\n'.format(seiyuuUri, 'wdt:P31', 'wd:Q5'))

		# seiyu_uri wdt:occupation wd:seiyu
		outputFile.write(u'<{0}> {1} {2} .\n'.format(seiyuuUri, 'wdt:P106', 'wd:Q622807'))

		# seiyu_uri rdfs:label name
		outputFile.write(u'<{0}> {1} "{2}"@{3} .\n'.format(seiyuuUri, "rdfs:label", seiyuu['seiyu_label']['value'], seiyuu['seiyu_label']['xml:lang']))

		# seiyu_uri wdt:mal_id mal_id
		if 'MAL_ID' in seiyuu:
			outputFile.write(u'<{0}> {1} <{2}> .\n'.format(seiyuuUri, "wdt:P4084", 'https://api.jikan.moe/person/' + str(seiyuu['MAL_ID']['value'])))

		if seiyuuData != None:
			if 'voice_acting_role' in seiyuuData:
				for work in seiyuuData['voice_acting_role']:
					animeURI = 'https://api.jikan.moe/anime/' + str(work['anime']['mal_id'])
					# anime_uri wdt:voice_actor seiyu_uri
					outputFile.write(u'<{0}> {1} <{2}> .\n'.format(animeURI, "wdt:P725", seiyuuUri))

		outputFile.write(u'\n')

if __name__ == '__main__':
	inputFileName = 'output.json'
	outputFileName = 'output.ttl'

	if len(sys.argv) >= 3:
		inputFileName = sys.argv[1]
		outputFileName = sys.argv[2] + '.ttl'

	main(inputFileName, outputFileName)