import sys
import requests
import io

import yaml
import json
import xmltodict
import xml.etree.ElementTree as ET

from SPARQLWrapper import SPARQLWrapper, JSON

# PREFIXES
rdfs = "http://www.w3.org/2000/01/rdf-schema#"
wdt = "http://www.wikidata.org/prop/direct/"
jikanAPI = "https://api.jikan.me/" 

def getSeiyuuListFromWikidata(limitTo):
	sparql = SPARQLWrapper("https://query.wikidata.org/sparql")

	queryString = """
	SELECT 
		?item 
		(SAMPLE(?label) AS ?itemLabel) 
		(SAMPLE(?Anime_News_Network_ID) AS ?ANN_ID) 
		(SAMPLE(?MyAnimeList_ID) AS ?MAL_ID) 
	WHERE {
		{?item wdt:P106 wd:Q622807.}

		?item rdfs:label ?label.
		FILTER(LANGMATCHES(LANG(?label), "en"))

		OPTIONAL { ?item wdt:P1982 ?Anime_News_Network_ID. }
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
		name = completeName[0]

	return name, surname

def getMalId(seiyu):
	return seiyu['MAL_ID']['value']

def getAnimeWorkedOnFor(seiyu):
	baseURL = 'https://api.jikan.me/person/'
	malId = getMalId(seiyu)

	response = json.loads(requests.get(baseURL + str(malId) + '/').text)
	
	animeWorkedOn = []

	for work in response['voice_acting_role']:
		animeWorkedOn.append(work['anime']['mal_id'])

	return animeWorkedOn

def seiyuInfoToTriples(seiyu):
	output = u''

	# seiyu_uri rdfs:label name
	output += u'<{0}> <{1}> <{2}>\n'.format(seiyu['item']['value'], rdfs + ":label", seiyu['itemLabel']['value'])

	# seiyu_uri wdt:ann_id ann_id
	# output += '<{0}> <{1}> <{2}>\n'.format(seiyu['item']['value'], wdt + ":P1982", seiyu['ANN_ID']['value'])

	# seiyu_uri wdt:mal_id mal_id
	output += u'<{0}> <{1}> <{2}>\n'.format(seiyu['item']['value'], wdt + ":P4084", jikanAPI + 'person/' + seiyu['MAL_ID']['value'])

	return output

def main(outputFileName, limitTo):
	seiyus = getSeiyuuListFromWikidata(limitTo)
	seiyusWithMalId = []

	# try to recover mal_id for seiyu that are missing it 
	for seiyu in seiyus:
		name, surname = getNameAndSurname(seiyu)
		
		if 'MAL_ID' not in seiyu:
			print('recovering MAL id of: ' + name + ' - ' + surname)
			malId = recoverMalId(seiyu)
			seiyu['MAL_ID'] = {"type": "literal", "value": str(malId)}
			
		if seiyu['MAL_ID']['value'] != -1:
			print('adding seiyu: ' + name + ' - ' + surname)
			seiyusWithMalId.append(seiyu)
		print('-----')

	# print(json.dumps(seiyus ,indent=2))

	outputFile = io.open(outputFileName, 'w', encoding="utf-8")

	for seiyu in seiyusWithMalId:
		outputFile.write(seiyuInfoToTriples(seiyu))

		animeWorkedOn = getAnimeWorkedOnFor(seiyu)
		animesOutput = u''
		for anime in animeWorkedOn:
			# seiyu_uri wdt:member_of anime_mal_id
			animesOutput += u'<{0}> <{1}> <{2}>\n'.format(seiyu['item']['value'], wdt + ":P463", jikanAPI + 'anime/' + str(anime))

		outputFile.write(animesOutput)

if __name__ == '__main__':
	outputFileName = 'output'
	limitTo = 1 # less or equal to 0 implies no limit

	if len(sys.argv) >= 2:
		outputFileName = sys.argv[1]

	if len(sys.argv) >= 3:
		limitTo = sys.argv[2]

	main(outputFileName, limitTo)