import sys

import yaml
import json

import matplotlib.pyplot as plt

def main(inputFileName):
	with open(inputFileName, 'rb') as f:
		graphicInfo = yaml.load(open(inputFileName, 'r'))

	measured = graphicInfo['xs']
	predicted = graphicInfo['ys']

	boundaries = graphicInfo['boundaries']

	color = graphicInfo['color']

	xlabel = graphicInfo['xlabel']
	ylabel = graphicInfo['ylabel']

	title = graphicInfo['title']
	
	outputFileName = graphicInfo['outputFileName']

	fig, ax = plt.subplots()
	ax.scatter(measured, predicted, edgecolors=(0, 0, 0))
	ax.plot(boundaries, boundaries, 'k--', lw=4)
	ax.set_xlabel('Measured')
	ax.set_ylabel('Predicted')

	plt.title(outputFileName)
	# plt.savefig('graphics/cart/predictions/{0}.png'.format(outputFileName), bbox_inches='tight', dpi=100)
	plt.show()
	# plt.close()

if __name__ == '__main__':

	if len(sys.argv) >= 2:
		inputFileName = sys.argv[1]

		main(inputFileName)