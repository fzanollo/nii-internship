import sys
import io

import yaml
import json

from SPARQLWrapper import SPARQLWrapper, JSON

def outputPrefixes():
	prefixes = [('rdfs', 'http://www.w3.org/2000/01/rdf-schema#'), ('wdt', 'http://www.wikidata.org/prop/direct/'), ('wd','http://www.wikidata.org/entity/')]
	prefixesForOutput = u''

	for prefix in prefixes:
		prefixesForOutput += u'@prefix {0}: <{1}> .\n'.format(prefix[0], prefix[1])

	prefixesForOutput += u'\n'
	return prefixesForOutput

def getPlaceLabel(placeUri):
	sparql = SPARQLWrapper("https://query.wikidata.org/sparql")
	
	query = """
	SELECT 
		(SAMPLE(?label) AS ?label)
	WHERE {{
		<{0}> rdfs:label ?label.
        FILTER(langmatches(LANG(?label), "en"))
	}}
	""".format(placeUri)

	sparql.setQuery(query)
	sparql.setReturnFormat(JSON)
	results = sparql.query().convert()

	bindings = yaml.load(json.dumps(results["results"]["bindings"]))

	label = None
	lang = None

	if len(bindings) > 0 and 'label' in bindings[0]:
		label = bindings[0]['label']['value']
		lang = bindings[0]['label']['xml:lang']

	return label, lang

def main(inputFileName, outputFileName):
	seiyuus = yaml.load(io.open(inputFileName, 'r', encoding="utf-8"))

	personalDataPerSeiyuu = yaml.load(io.open('jsonData/personalData.json', 'r', encoding="utf-8"))

	outputFile = io.open(outputFileName, 'w', encoding="utf-8")
	outputFile.write(outputPrefixes())

	count = 0
	placeLabels = {}

	for seiyuu in seiyuus:
		#para ver cuanto va
		if count % 10 ==0:
			print(count)
		count+=1

		seiyuuUri = seiyuu['seiyu_uri']['value']
		
		if seiyuuUri in personalDataPerSeiyuu:
			personalData = personalDataPerSeiyuu[seiyuuUri]

			if 'gender' in personalData:
				# seiyu_uri wdt:sex_or_gender gender
				outputFile.write(u'<{0}> {1} <{2}> .\n'.format(seiyuuUri, 'wdt:P21', personalData['gender']))

			if 'dateOfBirth' in personalData:
				# seiyu_uri wdt:date_of_birth date(literal)
				outputFile.write(u'<{0}> {1} "{2}" .\n'.format(seiyuuUri, 'wdt:P569', personalData['dateOfBirth']))

			if 'placeOfBirth' in personalData:
				placeOfBirthUri = personalData['placeOfBirth']

				# seiyu_uri wdt:place_of_birth place
				outputFile.write(u'<{0}> {1} <{2}> .\n'.format(seiyuuUri, 'wdt:P19', placeOfBirthUri))

				if placeOfBirthUri not in placeLabels:
					placeLabel, lang = getPlaceLabel(placeOfBirthUri)
					placeLabels[placeOfBirthUri] = {'label': placeLabel, 'lang': lang}

			outputFile.write(u'\n')
			
	for placeUri, placeData in placeLabels.iteritems():
		placeLabel = placeData['label'] 
		if placeLabel != None:
			# placeUri rdfs:label name
			outputFile.write(u'<{0}> {1} "{2}"@{3} .\n'.format(placeOfBirthUri, "rdfs:label", placeLabel, placeData['lang']))

if __name__ == '__main__':
	inputFileName = 'output.json'
	outputFileName = 'output.ttl'

	if len(sys.argv) >= 3:
		inputFileName = sys.argv[1]
		outputFileName = sys.argv[2] + '.ttl'

	main(inputFileName, outputFileName)