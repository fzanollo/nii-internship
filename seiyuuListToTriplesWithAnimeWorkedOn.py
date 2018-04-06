import sys
import requests
import io

import yaml
import json

API_CONSULTS_COUNTER = 0

def consultAPI(query):
	global API_CONSULTS_COUNTER

	response = json.loads(requests.get(query).text)
	API_CONSULTS_COUNTER += 1
	
	if 'error' in response:
		print(u'\n api error: [{0}] when asking for query: [{1}] with API_CONSULTS_COUNTER: {2}\n'.format(response['error'], query, API_CONSULTS_COUNTER))

	return response

def recoverMalId(seiyu):
	name, surname = getNameAndSurname(seiyu)

	baseURL = "https://api.jikan.me/search/people/"
	currentPage = 1

	response = consultAPI(baseURL + surname + '/' + str(currentPage))
	
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
			
			if currentPage <= lastPage:
				response = consultAPI(baseURL + surname + '/' + str(currentPage))

	return malId

def getNameAndSurname(seiyu):
	name = surname = None

	completeName = seiyu['itemLabel']['value'].replace(u'\u014d', 'ou').replace(u'\u016b', 'uu').split(' ')
	
	if len(completeName) >= 2:
		name = completeName[0]
		surname = completeName[1]
	else:
		surname = completeName[0]

	return name, surname

def getMalId(seiyu):
	return seiyu['MAL_ID']['value']

def getAnimeWorkedOnFor(seiyu):
	baseURL = 'https://api.jikan.me/person/'
	malId = getMalId(seiyu)

	response = consultAPI(baseURL + str(malId) + '/')
	
	animeWorkedOn = []

	if 'voice_acting_role' in response:
		for work in response['voice_acting_role']:
			animeWorkedOn.append(work['anime']['mal_id'])

	return animeWorkedOn

def outputPrefixes():
	prefixes = [('rdfs', 'http://www.w3.org/2000/01/rdf-schema#'), ('wdt', 'http://www.wikidata.org/prop/direct/'), ('jikan', 'https://api.jikan.me/' ),('wd','http://www.wikidata.org/entity/')]
	prefixesForOutput = u''

	for prefix in prefixes:
		prefixesForOutput += u'@prefix {0}: <{1}> .\n'.format(prefix[0], prefix[1])

	prefixesForOutput += u'\n'
	return prefixesForOutput

def seiyuInfo(seiyu):
	output = u''

	# seiyu_uri wdt:instance_of wd:human
	output += u'<{0}> {1} {2} .\n'.format(seiyu['item']['value'], 'wdt:P31', 'wd:Q5')

	# seiyu_uri wdt:occupation wd:seiyu
	output += u'<{0}> {1} {2} .\n'.format(seiyu['item']['value'], 'wdt:P106', 'wd:Q622807')

	# seiyu_uri rdfs:label name
	output += u'<{0}> {1} "{2}"@{3} .\n'.format(seiyu['item']['value'], "rdfs:label", seiyu['itemLabel']['value'], seiyu['itemLabel']['xml:lang'])

	# seiyu_uri wdt:mal_id mal_id
	if seiyu['MAL_ID']['value'] != -1:
		output += u'<{0}> {1} <{2}> .\n'.format(seiyu['item']['value'], "wdt:P4084", 'jikan:person/' + str(seiyu['MAL_ID']['value']))

	return output

def animeWorkedOn(seiyu):
	animeWorkedOn = getAnimeWorkedOnFor(seiyu)

	output = u''
	for anime in animeWorkedOn:
		animeURI = 'jikan:anime/' + str(anime)
		# seiyu_uri wdt:member_of anime_mal_id
		output += u'<{0}> {1} <{2}> .\n'.format(seiyu['item']['value'], "wdt:P463", animeURI)

	return output

def main(inputFileName, outputFileName, fromSeiyuIndex, toSeiyuIndex, limitToApiConsults):
	global API_CONSULTS_COUNTER
	seiyus = yaml.load(io.open(inputFileName, 'r', encoding="utf-8"))

	outputFile = io.open(outputFileName, 'w', encoding="utf-8")
	outputFile.write(outputPrefixes())

	for i in xrange(fromSeiyuIndex, min(toSeiyuIndex, len(seiyus))):
		seiyu = seiyus[i]

	 	if 'MAL_ID' not in seiyu:
	 		malId = recoverMalId(seiyu)
			seiyu['MAL_ID'] = {"type": "literal", "value": malId}

		outputFile.write(seiyuInfo(seiyu))

		if getMalId(seiyu) != -1:
			outputFile.write(animeWorkedOn(seiyu))

		outputFile.write(u'\n')

		print('Seiyu number: {0}, API_CONSULTS_COUNTER: {1}'.format(i, API_CONSULTS_COUNTER))
		if API_CONSULTS_COUNTER >= limitToApiConsults:
			break

	print('API_CONSULTS_COUNTER = ' + str(API_CONSULTS_COUNTER))
	print('last seiyu added = ' + str(i))

if __name__ == '__main__':
	inputFileName = 'output.json'
	outputFileName = 'output.ttl'
	fromSeiyuIndex = 0
	toSeiyuIndex = 10000
	limitToApiConsults = 5000

	if len(sys.argv) >= 6:
		inputFileName = sys.argv[1]
		outputFileName = sys.argv[2] + '.ttl'
		fromSeiyuIndex = int(sys.argv[3])
		toSeiyuIndex = int(sys.argv[4])
		limitToApiConsults = int(sys.argv[5])
		
		main(inputFileName, outputFileName, fromSeiyuIndex, toSeiyuIndex, limitToApiConsults)
	else:
		print('order of parameters: inputFileName outputFileName fromSeiyuIndex toSeiyuIndex limitToApiConsults')