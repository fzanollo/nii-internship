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

def recoverMalId(seiyuu):
	name, surname = getNameAndSurname(seiyuu)

	baseURL = "https://api.jikan.moe/search/people/"
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
				malId = person['mal_id']
				found = True

		if not found:
			currentPage += 1
			
			if currentPage <= lastPage:
				response = consultAPI(baseURL + surname + '/' + str(currentPage))

	return malId

def getNameAndSurname(seiyuu):
	name = surname = None

	completeName = seiyuu['seiyu_label']['value'].replace(u'\u014d', 'ou').replace(u'\u016b', 'uu').split(' ')
	
	if len(completeName) >= 2:
		name = completeName[0]
		surname = completeName[1]
	else:
		surname = completeName[0]

	return name, surname

def getUri(seiyuu):
	return seiyuu['seiyu_uri']['value']

def getSeiyuuInfo(seiyuu):
	response = {}

	if 'MAL_ID' not in seiyuu:
 		malId = recoverMalId(seiyuu)
		seiyuu['MAL_ID'] = {"type": "literal", "value": malId}

	if seiyuu['MAL_ID']['value'] != -1:
		baseURL = 'https://api.jikan.moe/person/'
		malId = seiyuu['MAL_ID']['value']

		response = consultAPI(baseURL + str(malId) + '/')
	
	return response

def main(inputFileName, outputFileName, fromSeiyuIndex, toSeiyuIndex, limitToApiConsults):
	global API_CONSULTS_COUNTER
	seiyuus = yaml.load(io.open(inputFileName, 'r', encoding="utf-8"))

	outputFile = io.open(outputFileName, 'w', encoding="utf-8")
	outputFile.write(u'[\n')

	upTo = min(toSeiyuIndex, len(seiyuus))
	
	for i in xrange(fromSeiyuIndex, upTo):
		seiyuu = seiyuus[i]

		info = getSeiyuuInfo(seiyuu)

		outputFile.write(u'{{ "id":"{0}", "data":{1} }}'.format(getUri(seiyuu), json.dumps(info, ensure_ascii=False)))

		if i < upTo-1:
			outputFile.write(u',')

		outputFile.write(u'\n')

		print('Seiyu number: {0}, API_CONSULTS_COUNTER: {1}'.format(i, API_CONSULTS_COUNTER))
		if API_CONSULTS_COUNTER >= limitToApiConsults:
			break

	outputFile.write(u'\n]')
	
	print('API_CONSULTS_COUNTER = ' + str(API_CONSULTS_COUNTER))
	print('last seiyuu added = ' + str(i))

if __name__ == '__main__':
	inputFileName = 'seiyuuList.json'
	outputFileName = 'output.json'
	fromSeiyuIndex = 0
	toSeiyuIndex = 10000
	limitToApiConsults = 5000

	if len(sys.argv) >= 6:
		inputFileName = sys.argv[1]
		outputFileName = sys.argv[2] + '.json'
		fromSeiyuIndex = int(sys.argv[3])
		toSeiyuIndex = int(sys.argv[4])
		limitToApiConsults = int(sys.argv[5])
		
		main(inputFileName, outputFileName, fromSeiyuIndex, toSeiyuIndex, limitToApiConsults)
	else:
		print('order of parameters: inputFileName outputFileName fromSeiyuIndex toSeiyuIndex limitToApiConsults')