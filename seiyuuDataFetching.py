import sys
import requests
import io
from sets import Set

import yaml
import json
import xmltodict
import xml.etree.ElementTree as ET

from SPARQLWrapper import SPARQLWrapper, JSON

def getSeiyuuListFromWikidata(limitTo):
	sparql = SPARQLWrapper("https://query.wikidata.org/sparql")

	queryString = """
	SELECT 
		?item 
		(SAMPLE(?label) AS ?itemLabel) 
		(SAMPLE(?MyAnimeList_ID) AS ?MAL_ID) 
	WHERE {
		{?item wdt:P106 wd:Q622807.}

		?item rdfs:label ?label.
		FILTER(LANGMATCHES(LANG(?label), "en"))
		OPTIONAL { ?item wdt:P4084 ?MyAnimeList_ID. }
	}
	GROUP BY ?item
	"""

	if limitTo > 0:
		queryString += "LIMIT {0}".format(limitTo)

	sparql.setQuery(queryString)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()

	bindings = yaml.load(json.dumps(results["results"]["bindings"]))
	return bindings

def recoverMalId(seiyu):
	name, surname = getNameAndSurname(seiyu)

	baseURL = "https://api.jikan.me/search/people/"
	currentPage = 1

	response = json.loads(requests.get(baseURL + surname + '/' + str(currentPage)).text)
	
	lastPage = 0
	malId = -1
	found = False

	if 'result_last_page' in response:
		lastPage = response['result_last_page']

	while not found and currentPage <= lastPage and name != None and surname != None:
		for person in response['result']:
			if person['name'] == (surname + ', ' + name):
				malId = person['id']
				found = True

		if not found:
			currentPage += 1
			response = json.loads(requests.get(baseURL + surname + '/' + str(currentPage)).text)

	return malId

def getNameAndSurname(seiyu):
	name = surname = None

	completeName = seiyu['itemLabel']['value'].replace(u'\u014d', 'ou').replace(u'\u016b', 'uu').split(' ')
	
	if len(completeName) >= 2:
		name, surname = completeName
	else:
		surname = completeName[0]

	return name, surname

def getMalId(seiyu):
	return seiyu['MAL_ID']['value']

def getAnimeWorkedOnFor(seiyu):
	baseURL = 'https://api.jikan.me/person/'
	malId = getMalId(seiyu)

	response = json.loads(requests.get(baseURL + str(malId) + '/').text)
	
	animeWorkedOn = []

	if 'voice_acting_role' in response:
		for work in response['voice_acting_role']:
			animeWorkedOn.append(work['anime']['mal_id'])

	return animeWorkedOn

def seiyuInfoToTriples(seiyu):
	output = u'\n'

	# seiyu_uri wdt:instance_of wd:human
	output += u'<{0}> {1} {2} .\n'.format(seiyu['item']['value'], 'wdt:P31', 'wd:Q5')

	# seiyu_uri wdt:occupation wd:seiyu
	output += u'<{0}> {1} {2} .\n'.format(seiyu['item']['value'], 'wdt:P106', 'wd:Q622807')

	# seiyu_uri rdfs:label name
	output += u'<{0}> {1} "{2}"@{3} .\n'.format(seiyu['item']['value'], "rdfs:label", seiyu['itemLabel']['value'], seiyu['itemLabel']['xml:lang'])

	# seiyu_uri wdt:mal_id mal_id
	output += u'<{0}> {1} <{2}> .\n'.format(seiyu['item']['value'], "wdt:P4084", 'jikan:person/' + seiyu['MAL_ID']['value'])

	return output

def prefixes():
	prefixes = [('rdfs', 'http://www.w3.org/2000/01/rdf-schema#'), ('wdt', 'http://www.wikidata.org/prop/direct/'), ('jikan', 'https://api.jikan.me/' ),('wd','http://www.wikidata.org/entity/')]
	prefixesForOutput = u''

	for prefix in prefixes:
		prefixesForOutput += u'@prefix {0}: <{1}> .\n'.format(prefix[0], prefix[1])

	return prefixesForOutput

def main(outputFileName, limitTo):
	seiyus = getSeiyuuListFromWikidata(limitTo)
	seiyusWithMalId = []

	print('* Seiyu list received from wikidata *')

	# try to recover mal_id for seiyu that are missing it 
	for seiyu in seiyus:
		name, surname = getNameAndSurname(seiyu)
		
		if 'MAL_ID' not in seiyu:
			# print('recovering MAL id of: ' + name + ' - ' + surname)
			malId = recoverMalId(seiyu)
			seiyu['MAL_ID'] = {"type": "literal", "value": str(malId)}
			
		if seiyu['MAL_ID']['value'] != -1:
			# print('adding seiyu: ' + name + ' - ' + surname)
			seiyusWithMalId.append(seiyu)
		# print('-----')

	# print(json.dumps(seiyus ,indent=2))

	print(str(len(seiyusWithMalId)) + ' seiyu with mal_id information retrieved')

	animeURIs = Set()

	outputFile = io.open(outputFileName, 'w', encoding="utf-8")
	outputFile.write(prefixes())

	for seiyu in seiyusWithMalId:
		outputFile.write(seiyuInfoToTriples(seiyu))

		animeWorkedOn = getAnimeWorkedOnFor(seiyu)

		animeWorkedOnOutput = u''
		for anime in animeWorkedOn:
			animeURI = 'jikan:anime/' + str(anime)
			animeURIs.add(animeURI)
			# seiyu_uri wdt:member_of anime_mal_id
			animeWorkedOnOutput += u'<{0}> {1} <{2}> .\n'.format(seiyu['item']['value'], "wdt:P463", animeURI)

		outputFile.write(animeWorkedOnOutput)

	print(str(len(animeURIs)) + ' total anime')

	outputFile.write(u'\n')
	for animeURI in animeURIs:
		# anime_uri wdt:instance_of wd:anime
		outputFile.write(u'<{0}> {1} {2} .\n'.format(animeURI, 'wdt:P31', 'wd:Q1107'))


if __name__ == '__main__':
	outputFileName = 'output.ttl'
	limitTo = 1 # less or equal to 0 implies no limit

	if len(sys.argv) >= 2:
		outputFileName = sys.argv[1] + '.ttl'

	if len(sys.argv) >= 3:
		limitTo = int(sys.argv[2])

	main(outputFileName, limitTo)