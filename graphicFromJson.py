import sys

import yaml

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import matplotlib.ticker as plticker

def main(inputFileName):

	with open(inputFileName, 'rb') as f:
		graphicInfo = yaml.load(open(inputFileName, 'r'))

	xs = graphicInfo['xs']
	ys = graphicInfo['ys']

	color = graphicInfo['color']

	xlabel = graphicInfo['xlabel']
	ylabel = graphicInfo['ylabel']

	title = graphicInfo['title']
	
	outputFileName = graphicInfo['outputFileName']

	# PLOT
	plt.figure()
	plt.plot(xs,ys,'{0}-'.format(color))

	# X TICKS
	plt.xticks([])

	# Y TICKS
	ax = plt.gca()
	ax.yaxis.set_major_locator(MaxNLocator(integer=True))
	ax.yaxis.grid(which="major", color='k', linestyle='-', linewidth=.2)
	ax.set_ylim(ymin=0)
	if 'ytickInterval' in graphicInfo:
		ytickInterval = graphicInfo['ytickInterval']
		loc = plticker.MultipleLocator(base=ytickInterval)
		ax.yaxis.set_minor_locator(loc)
		ax.yaxis.grid(which="minor", color='k', linestyle='-', linewidth=.1)

	# LABELS
	plt.xlabel(xlabel)
	plt.ylabel(ylabel)

	# TITLE
	plt.title(title)
	plt.savefig('graphics/{0}.png'.format(outputFileName))
	# plt.show()

	plt.close()

if __name__ == '__main__':

	if len(sys.argv) >= 2:
		inputFileName = sys.argv[1]
		main(inputFileName)
	else:
		print('missing name of file to graphic')

# for file in aux/*.json; do python graphicFromJson.py $file; done