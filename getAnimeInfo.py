import sys
import requests
import io

import yaml
import json
import time

API_CONSULTS_COUNTER = 0

def consultAPI(query):
	global API_CONSULTS_COUNTER

	response = json.loads(requests.get(query).text)
	API_CONSULTS_COUNTER += 1
	
	if 'error' in response:
		print(u'\n api error: [{0}] when asking for query: [{1}] with API_CONSULTS_COUNTER: {2}\n'.format(response['error'], query, API_CONSULTS_COUNTER))

	time.sleep(2)

	return response

def main(inputFileName, outputFileName, fromAnimeIndex, toAnimeIndex, limitToApiConsults):
	global API_CONSULTS_COUNTER

	animeUris = yaml.load(io.open(inputFileName, 'r', encoding="utf-8"))

	outputFile = io.open(outputFileName, 'w', encoding="utf-8")
	outputFile.write(u'[\n')

	upTo = min(toAnimeIndex, len(animeUris))

	for i in xrange(fromAnimeIndex, upTo):
		animeUri = animeUris[i]['anime_uri']['value']

		animeData = consultAPI(animeUri)

		outputFile.write(u'{{ "id":"{0}", "data":{1} }}'.format(animeUri, json.dumps(animeData, ensure_ascii=False)))

		if i < upTo-1:
			outputFile.write(u',')
		
		outputFile.write(u'\n')

		print('Anime number: {0}, API_CONSULTS_COUNTER: {1}'.format(i, API_CONSULTS_COUNTER))
		if API_CONSULTS_COUNTER >= limitToApiConsults:
			break

	outputFile.write(u'\n]')

	print('API_CONSULTS_COUNTER = ' + str(API_CONSULTS_COUNTER))
	print('last anime added = ' + str(i))

if __name__ == '__main__':
	inputFileName = 'animeList.json'
	outputFileName = 'output.json'
	fromAnimeIndex = 0
	toAnimeIndex = 1000000
	limitToApiConsults = 5000

	if len(sys.argv) >= 5:
		outputFileName = sys.argv[1] + '.json'
		fromAnimeIndex = int(sys.argv[2])
		toAnimeIndex = int(sys.argv[3])
		limitToApiConsults = int(sys.argv[4])
		
		main(inputFileName, outputFileName, fromAnimeIndex, toAnimeIndex, limitToApiConsults)
	else:
		print('order of parameters: outputFileName fromAnimeIndex toAnimeIndex limitToApiConsults')