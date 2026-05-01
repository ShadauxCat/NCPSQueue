import plotly
import locale
import time
import random
import sys
import math
import itertools
from decimal import *
import argparse
import os
import re
import collections

parser = argparse.ArgumentParser()
parser.add_argument("datafile", help="File containing output from QueueTests")
parser.add_argument("--greyscale", "-g", help="Output greyscale images", action="store_true")
parser.add_argument("--comp-only", "-c", help="Skip individual charts and only output comparisons", action="store_true")
parser.add_argument("--height", "-e", help="Specify image height", type=int, default=1080)
parser.add_argument("--width", "-w", help="Specify image height", type=int, default=1920)
parser.add_argument("--spline", "-s", help="Smooth line graphs", action="store_true")
parser.add_argument("--no-singles", '-n', help="Exclude results with 1 producer and 1 consumer", action="store_true")
parser.add_argument("--filter", "-f", help="Exclude types including this substring", nargs="*", action="extend", default=[])
parser.add_argument("--neg-filter", "-F", help="Exclude types not including this substring", nargs="*", action="extend", default=[])
parser.add_argument("--max-compare-cores", help="Maximum total cores to use in comparison graphs", default=24, type=int)
parser.add_argument("--builtin-filter-batch-cmp", "-B", help="Run a batch comparison. Equivalent to --neg-filter='[Batch'", action="store_true")
parser.add_argument("--builtin-filter-single-cmp", "-S", help="Run a single-item comparison. Equivalent to --filter='[Batch'", action="store_true")
parser.add_argument("--builtin-filter-competitive-cmp", "-C", help="Run a competitive comparison, comparing only the best configurations for each queue. Does some more complex filtering to include only those items.", action="store_true")
args = parser.parse_args()

locale.setlocale(locale.LC_ALL, '')

greyscale = args.greyscale
lineShape = "spline" if args.spline else "linear"
compOnly = args.comp_only

imageWidth = args.width
imageHeight = args.height
no_singles = args.no_singles

if args.builtin_filter_batch_cmp:
	args.neg_filter.append('[Batch')
if args.builtin_filter_single_cmp:
	args.filter.append('[Batch')

legendAttrs = dict(
	font=dict(
		family='sans-serif',
		size=9,
		color='#000'
	)
)
titleAttrs = dict()
if imageWidth <= 600:
	legendAttrs['orientation'] = 'h'
	titleAttrs = dict(
		size=12
	)
typeColor = "#0000ff"
legendDetailBackground = "#ffffff"

enqueueData = {}
dequeueData = {}
dequeueEmptyData = {}
latencyData = {}
symmetricData = {}
prodOverConData = {}
conOverProdData = {}
prodWayOverConData = {}
conWayOverProdData = {}
	
colorscale = [
	[0.0, 'rgb(0,0,0)'],
	[0.2, 'rgb(49,54,149)'], 
	[0.25, 'rgb(69,117,180)'], 
	[0.3, 'rgb(116,173,209)'], 
	[0.35, 'rgb(171,217,233)'], 
	[0.4, 'rgb(224,243,248)'], 
	[0.45, 'rgb(254,224,144)'], 
	[0.5, 'rgb(253,174,97)'], 
	[0.733, 'rgb(244,109,67)'], 
	[0.867, 'rgb(215,48,39)'], 
	[1.0, 'rgb(165,0,38)']
]

visuallyDistinctColors = [
	"hsv(0, 100%, 100%)",
	"hsv(30, 100%, 100%)",
	"hsv(60, 100%, 75%)",
	#"hsv(90, 100%, 100%)",
	"hsv(120, 100%, 50%)",
	#"hsv(150, 100%, 100%)",
	"hsv(180, 100%, 75%)",
	"hsv(210, 100%, 100%)",
	"hsv(240, 100%, 100%)",
	"hsv(270, 100%, 100%)",
	"hsv(300, 100%, 100%)",
	"hsv(330, 100%, 100%)",
	
	"hsv( 15, 75%, 100%)",
	"hsv( 45, 75%, 75%)",
	"hsv( 75, 75%, 75%)",
	#"hsv(105, 75%, 100%)",
	"hsv(135, 75%, 100%)",
	#"hsv(165, 75%, 100%)",
	"hsv(195, 75%, 100%)",
	"hsv(225, 75%, 100%)",
	"hsv(255, 75%, 100%)",
	"hsv(285, 75%, 100%)",
	"hsv(315, 75%, 100%)",
	"hsv(345, 75%, 100%)",
]

lineColors = collections.OrderedDict()

if greyscale:
	colorscale = [
		[0.0, 'rgb(255,255,255)'], 
		[0.1, 'rgb(225,225,225)'], 
		[0.2, 'rgb(200,200,200)'], 
		[0.3, 'rgb(175,175,175)'], 
		[0.4, 'rgb(150,150,150)'], 
		[0.5, 'rgb(125,125,125)'], 
		[0.6, 'rgb(100,100,100)'], 
		[0.7, 'rgb(75,75,75)'], 
		[0.8, 'rgb(50,50,50)'],
		[0.9, 'rgb(25,25,25)'],
		[1.0, 'rgb(0,0,0)']
	]
	visuallyDistinctColors = [
		"rgb(0,0,0)", "rgb(20,20,20)", "rgb(40,40,40)", 
		"rgb(60,60,60)", "rgb(80,80,80)", "rgb(100,100,100)",
		"rgb(120,120,120)", "rgb(140,140,140)", "rgb(160,160,160)",
		"rgb(180,180,180)"
	]
	typeColor = "rgb(128, 128, 128)"
	legendDetailBackground = "rgb(196, 196, 196)"

data = collections.OrderedDict()

maxes = {}

mins = {}

allMax = { "enqueue": 0, "dequeue": 0, "enq+deq": 0, "deq_empty": 0, "latency": 0 }
allMin = { "enqueue": 9999999999999, "dequeue": 9999999999999, "enq+deq": 9999999999999, "deq_empty": 9999999999999, "latency": 0 }

maxProd = 0
maxCon = 0

types = ["char", "int64_t", "FixedStaticString"]
def get_name(id):
	return id

def GetElementType(type):
	if "char" in type:
		return types[0]
	elif "long" in type or "__int64" in type:
		return types[1]
	else:
		return types[2]
		
with open(args.datafile, 'r') as f:
	text = f.read()
	
idx = 0
lastElemType = None

import colorsys

def get_distinct_colors(num):
	def MidSort(lst):
		if len(lst) <= 1:
			return lst
		i = int(len(lst)/2)
		ret = [lst.pop(i)]
		left = MidSort(lst[0:i])
		right = MidSort(lst[i:])
		interleaved = [item for items in itertools.zip_longest(left, right)
			for item in items if item != None]
		ret.extend(interleaved)
		return ret

	# Build list of points on a line (0 to 255) to use as color 'ticks'
	max = 255
	segs = int(num**(Decimal("1.0")/3))
	step = int(max/segs)
	p = [(i*step) for i in range(1,segs)]
	points = [0,max]
	points.extend(MidSort(p))

	# Not efficient!!! Iterate over higher valued 'ticks' first (the points
	#   at the front of the list) to vary all colors and not focus on one channel.
	colors = ["#%02X%02X%02X" % (points[0], points[0], points[0])]
	colorRange = 0
	total = 1
	while total < num and colorRange < len(points):
		colorRange += 1
		for c0 in range(colorRange):
			for c1 in range(colorRange):
				for c2 in range(colorRange):
					if total >= num:
						break
					c = "#%02X%02X%02X" % (points[c0], points[c1], points[c2])
					if c not in colors:
						colors.append(c)
						total += 1
	return colors

import re

printed = set()

for line in text.splitlines():

	if line.strip() == "":
		continue

	if line.startswith("|") or line.startswith("-") or line.startswith("QUEUE"):
		continue

	try:
		split = line.split('\t')

		name = split[0].strip()
		type = split[1].strip()
		
		elemType = GetElementType(name);
		if elemType != lastElemType:
			lastElemType = elemType
			idx = 0
		
		good = True
		for filter in args.filter:
			if filter in name:
				good = False
				break
		for filter in args.neg_filter:
			if filter not in name:
				good = False
				break
		if not good:
			continue
		
		
		if name not in lineColors:
			lineColors[name] = visuallyDistinctColors[idx % len(visuallyDistinctColors)]
			idx += 1
			
		producers = int(split[2].strip())
		consumers = int(split[3].strip())
		throughput = float(split[4].strip())
		
		skip = False
		if no_singles:
			if (producers == 1 or consumers == 1) and type == 'enq+deq':
				skip = True
			elif producers == 1 and consumers == 1 and type != "latency":
				skip = True
			
		if skip:
			throughput = None
			min_throughput = None
			max_throughput = None
		else:
			min_throughput = float(split[5].strip())
			max_throughput = float(split[6].strip())
			
			if type == "enq+deq":
				maxProd = max(maxProd, producers)
				maxCon = max(maxCon, consumers)
				
			d = maxes.setdefault(name, { "enqueue": 0, "dequeue": 0, "enq+deq": 0, "deq_empty": 0, "latency": 0 })
			d[type] = max(max_throughput, d[type])
			allMax[type] = max(max_throughput, allMax[type])
		
			d = mins.setdefault(name, { "enqueue": 9999999999999, "dequeue": 9999999999999, "enq+deq": 9999999999999, "deq_empty": 9999999999999, "latency": 9999999999999 })
			d[type] = min(min_throughput, d[type])
			allMin[type] = min(min_throughput, allMin[type])
		
		data.setdefault(name, {}).setdefault(type, []).append((producers, consumers, throughput, min_throughput, max_throughput))
	except IndexError:
		print(line)
		raise

def intWithCommas(x):
	if x is None:
		return '';
	return f"{x:,}"

allowedComparisons=[
	"std::deque",
	"1024cores",
	"tbb",
	"tbb-bounded",
	"michael_scott_queue",
	"nikolaev_bounded_queue",
	"ramalhete_queue",
	"MoodyCamelWithSize-8192",
	"BEAST-8192",
	"BEAST-1000000",
	"BEAST-bounded-131072",
	"BEAST-bounded-1000000"
]

latencyKeys = {}
latencyVals = {}
latencyMin = {}
latencyMax = {}
latencyTxt = {}

def FormatLargeNumber(num):
	if num is None:
		return ""
	num = float(num)
	if num >= 1000000000:
		num /= 1000000000
		return f"{num:.2f}B"
	if num >= 1000000:
		num /= 1000000
		return f"{num:.2f}M"
	if num >= 1000:
		num /= 1000
		return f"{num:.2f}K"
	return f"{num:.2f}"

patterns = [ "", "/", "\\", "x", "-", "|", "+", "." ]
patternIdx = -1
patternLock = {}

def print_graphs(name, d, minVal, maxVal):
	for type, listOfDatapoints in d.items():
		keys = []
		vals = []
		minVals = []
		maxVals = []
		sizes = []
		texts = []
		elementType = GetElementType(name)
		
		printName = name.replace("moodycamel::ConcurrentQueue", "moodycamel")
		printName = printName.replace("MoodyCamelWithSize", "moodycamel")
		printName = printName.replace("BEAST::ConcurrentQueue", "BEAST")
		printName = printName.replace("::ConcurrentBoundedQueue", "-bounded")
		printName = printName.replace("ext_", "")
		printName = printName.replace("::mpmc_bounded_queue", "")
		printName = printName.replace("::detail::d2::concurrent_bounded_queue", "-bounded")
		printName = printName.replace("::detail::d2::concurrent_queue", "")
		printName = printName.replace("xenium::", "")

		if args.builtin_filter_competitive_cmp:
			noComp = False
			baseName = printName.split(" ")[0]
			sizeCheck = printName.split("size ")
			if len(sizeCheck) == 2:
				size = sizeCheck[1].split(")")[0]
				size = size.split(",")[0]
				baseName += "-" + size
			if "+b" in name and "[Batch" not in name:
				noComp = True
			elif "+n" in name or "[Ephemeral Tickets]" in name or "[Dynamic]" in name or "[No Tickets]" in name:
				noComp = True
			else:
				noComp = baseName not in allowedComparisons
			if noComp:
				continue

		if printName not in patternLock:
			global patternIdx
			patternIdx += 1
			patternLock[printName] = patterns[patternIdx % len(patterns)]

		pattern = patternLock[printName]

		if type == "latency":
			for dataPoints in listOfDatapoints:
				lineColors[printName] = lineColors[name]
				latencyKeys.setdefault(elementType, []).append(printName)
				latencyVals.setdefault(elementType, []).append(dataPoints[2])
				latencyMin.setdefault(elementType, []).append(dataPoints[2]-dataPoints[3])
				latencyMax.setdefault(elementType, []).append(dataPoints[4]-dataPoints[2])
				latencyTxt.setdefault(elementType, []).append(
					"{}ns".format(FormatLargeNumber(dataPoints[2]))
				)

		elif type == "enqueue" or type == "dequeue" or type == "deq_empty":
			for dataPoints in listOfDatapoints:
				if type == "enqueue":
					if args.no_singles and dataPoints[0] == 1:
						continue
					keys.append(dataPoints[0])
				else:
					if args.no_singles and dataPoints[1] == 1:
						continue
					keys.append(dataPoints[1])
				vals.append(dataPoints[2])
				if dataPoints[2] == None:
					minVals.append(0)
					maxVals.append(0)
					texts.append("")
				else:
					minVals.append(dataPoints[2]-dataPoints[3])
					maxVals.append(dataPoints[4]-dataPoints[2])

					texts.append(
						"{}op/s".format(FormatLargeNumber(dataPoints[2]))
					)
				
			trace = plotly.graph_objs.Bar(
				x=keys,
				y=vals,
				error_y = dict(
					type="data",
					symmetric=False,
					array=maxVals,
					arrayminus=minVals
				),
				name=printName,
				hoverlabel = dict(namelength = -1),
				text=texts,
				marker_pattern_shape=pattern,
				marker=dict(color=lineColors[name]),
			)
			
			if type == "enqueue":
				enqueueData.setdefault(elementType, []).append(trace)
			elif type == "dequeue":
				dequeueData.setdefault(elementType, []).append(trace)
			elif type == "deq_empty":
				dequeueEmptyData.setdefault(elementType, []).append(trace)
			else:
				latencyData.setdefault(elementType, []).append(trace)

			if type != "latency":
				dir = os.path.join("gen_html", type, elementType)
				if not os.path.exists(dir):
					os.makedirs(dir)

				trace = plotly.graph_objs.Scatter(
					x=keys,
					y=vals,
					text=texts,
					name=printName,
					mode = 'lines+markers',
					hoverlabel = dict(namelength = -1)
				)

				if type == "deq_empty":
					label = "Dequeue From Empty"
				else:
					label = type.title()

				layout = plotly.graph_objs.Layout(
					title = '{} ({} <{}>)'.format(label, printName, elementType),
					xaxis = dict(
						title = 'Threads',
						tickformat = ',d'
					),
					yaxis = dict(
						title = 'Throughput (ops/s)',
					),
					#annotations=annotations,
					#barmode = 'group',
					barcornerradius=15,
					#legend=legendAttrs,
					#titlefont = titleAttrs
				)
				fig = plotly.graph_objs.Figure(
					data = [trace],
					layout = layout
				)
				plotly.offline.plot(
					fig,
					filename = os.path.join(dir, '{}_{}_{}.html'.format(printName.replace("::", "-"), type, elementType)),
					image='png', image_filename='{}_{}_{}'.format(printName.replace("::", "-"), type,elementType), image_height=imageHeight, image_width=imageWidth
				)
		elif type == "enq+deq":
			colors = []
			global heatmap
			heatmap = []
			heatmaptxt = []
			
			symmetrics = []
			symMax = []
			symMin = []
			symText = []
			prodOverCons = []
			pOCMax = []
			pOCMin = []
			pOCText = []
			conOverProds = []
			cOPMax = []
			cOPMin = []
			cOPText = []
			prodWayOverCons = []
			pWOCMax = []
			pWOCMin = []
			pWOCText = []
			conWayOverProds = []
			cWOPMax = []
			cWOPMin = []
			cWOPText = []
			for dataPoints in listOfDatapoints:
				if dataPoints[0] + dataPoints[1] <= args.max_compare_cores:
					if dataPoints[0] == dataPoints[1]:
						symmetrics.append(dataPoints[2])
						symMin.append(dataPoints[3])
						symMax.append(dataPoints[4])
						symText.append(FormatLargeNumber(dataPoints[2]))
					elif dataPoints[0] == dataPoints[1] * 2:
						prodOverCons.append(dataPoints[2])
						pOCMin.append(dataPoints[3])
						pOCMax.append(dataPoints[4])
						pOCText.append(FormatLargeNumber(dataPoints[2]))
					elif dataPoints[0] * 2 == dataPoints[1]:
						conOverProds.append(dataPoints[2])
						cOPMax.append(dataPoints[3])
						cOPMin.append(dataPoints[4])
						cOPText.append(FormatLargeNumber(dataPoints[2]))
					elif dataPoints[0] == dataPoints[1] * 3:
						prodWayOverCons.append(dataPoints[2])
						pWOCMin.append(dataPoints[3])
						pWOCMax.append(dataPoints[4])
						pWOCText.append(FormatLargeNumber(dataPoints[2]))
					elif dataPoints[0] * 3 == dataPoints[1]:
						conWayOverProds.append(dataPoints[2])
						cWOPMax.append(dataPoints[3])
						cWOPMin.append(dataPoints[4])
						cWOPText.append(FormatLargeNumber(dataPoints[2]))

				keys.append(dataPoints[0])
				vals.append(dataPoints[1])

				while len(heatmap) <= dataPoints[1]:
					heatmap.append([])
					heatmaptxt.append([])
				while len(heatmap[dataPoints[1]]) <= dataPoints[0]:
					heatmap[dataPoints[1]].append(None)
					heatmaptxt[dataPoints[1]].append(None)
					
				heatmap[dataPoints[1]][dataPoints[0]] = dataPoints[2]
				heatmaptxt[dataPoints[1]][dataPoints[0]] = "throughput: {}op/s".format(intWithCommas(dataPoints[2]))
				
				if dataPoints[2] is None:
					colors.append(0)
					sizes.append(0)
					texts.append('')
				else:
					colors.append(dataPoints[2])
					sizes.append(float(dataPoints[2])/float(allMax[type]) * ((imageHeight - 200) / max(maxProd, maxCon)))
					texts.append(
						"throughput: {}op/s".format(intWithCommas(dataPoints[2]))
					)

			compKeys = [x*2 for x in range(1,len(symmetrics)+1)]
			trace = plotly.graph_objs.Bar(
				x=compKeys,
				y=symmetrics,
				error_y=dict(
					type="data",
					symmetric=False,
					array=maxVals,
					arrayminus=minVals
				),
				name=printName,
				hoverlabel=dict(namelength=-1),
				text=symText,
				marker_pattern_shape=pattern,
				marker=dict(color=lineColors[name]),
			)
			symmetricData.setdefault(elementType, []).extend([trace])

			compKeys = [x*3 for x in range(1,len(prodOverCons)+1)]
			trace = plotly.graph_objs.Bar(
				x=compKeys,
				y=prodOverCons,
				error_y=dict(
					type="data",
					symmetric=False,
					array=maxVals,
					arrayminus=minVals
				),
				name=printName,
				hoverlabel=dict(namelength=-1),
				text=pOCText,
				marker_pattern_shape=pattern,
				marker=dict(color=lineColors[name]),
			)
			prodOverConData.setdefault(elementType, []).extend([trace])

			compKeys = [x*3 for x in range(1,len(conOverProds)+1)]
			trace = plotly.graph_objs.Bar(
				x=compKeys,
				y=conOverProds,
				error_y=dict(
					type="data",
					symmetric=False,
					array=maxVals,
					arrayminus=minVals
				),
				name=printName,
				hoverlabel=dict(namelength=-1),
				text=cOPText,
				marker_pattern_shape=pattern,
				marker=dict(color=lineColors[name]),
			)
			conOverProdData.setdefault(elementType, []).extend([trace])

			compKeys = [x*4 for x in range(1,len(prodWayOverCons)+1)]
			trace = plotly.graph_objs.Bar(
				x=compKeys,
				y=prodWayOverCons,
				error_y=dict(
					type="data",
					symmetric=False,
					array=maxVals,
					arrayminus=minVals
				),
				name=printName,
				hoverlabel=dict(namelength=-1),
				text=pWOCText,
				marker_pattern_shape=pattern,
				marker=dict(color=lineColors[name]),
			)
			prodWayOverConData.setdefault(elementType, []).extend([trace])

			compKeys = [x*4 for x in range(1,len(conWayOverProds)+1)]
			trace = plotly.graph_objs.Bar(
				x=compKeys,
				y=conWayOverProds,
				error_y=dict(
					type="data",
					symmetric=False,
					array=maxVals,
					arrayminus=minVals
				),
				name=printName,
				hoverlabel=dict(namelength=-1),
				text=cWOPText,
				marker_pattern_shape=pattern,
				marker=dict(color=lineColors[name]),
			)
			conWayOverProdData.setdefault(elementType, []).extend([trace])
			
			heatmap[0] = [None] * len(heatmap[1])
			
			trace = plotly.graph_objs.Heatmap(
				z = heatmap,
				text=heatmaptxt,
				colorscale=colorscale,
				zsmooth='best',
				zmin=0,
				zmax=allMax[type],
				texttemplate="%{z:.4s}"
			)
			trace2 = plotly.graph_objs.Scatter(
				x = [len(heatmap)-1, 0.5],
				y = [0.5, len(heatmap[1])-1],
				name = 'Overload line',
				mode = 'lines',
				line=dict(
					color = 'rgb(0, 0, 0)'
				)
			)
			
			data = [trace, trace2]
			layout = plotly.graph_objs.Layout(
				title = '{}<br>min: {}op/s<br>max: {}op/s'.format(
					printName, intWithCommas(mins[name][type]), intWithCommas(maxes[name][type])
				),
				xaxis = dict(
					title = 'Producer Threads',
					range = [1.5 if args.no_singles else 0.5,len(heatmap) - 0.5],
					tickformat = ',d'
				),
				yaxis = dict(
					title = 'Consumer Threads',
					range = [1.5 if args.no_singles else 0.5,len(heatmap[1]) - 0.5],
					tickformat = ',d'
				),
				hovermode = 'closest',
				#titlefont = titleAttrs
			)
			fig = plotly.graph_objs.Figure(
				data = data,
				layout = layout
			)
			if not compOnly:
				plotly.offline.plot(
					fig,
					filename = os.path.join(dir, printName.replace("::", "-") + "_" + get_name(type) + '_heatmap.html'),
					image='png', image_filename=printName.replace("::", "-") + "_" + elementType + '_heatmap', image_height=imageHeight, image_width=imageWidth
				)
				#time.sleep(5)

				def plot(keys, vals, texts, title, axisTitle, fileName):

					trace = plotly.graph_objs.Scatter(
						x=keys,
						y=vals,
						text=texts,
						name=printName,
						mode='lines+markers',
						hoverlabel=dict(namelength=-1)
					)

					layout = plotly.graph_objs.Layout(
						title=title,
						xaxis=dict(
							title=axisTitle,
							tickformat=',d'
						),
						yaxis=dict(
							title='Throughput (ops/s)',
						),
						# annotations=annotations,
						# barmode = 'group',
						barcornerradius=15,
						# legend=legendAttrs,
						# titlefont = titleAttrs
					)
					fig = plotly.graph_objs.Figure(
						data=[trace],
						layout=layout
					)
					plotly.offline.plot(
						fig,
						filename=os.path.join(dir, '{}_{}_{}.html'.format(printName.replace("::", "-"), fileName, elementType)),
						image='png', image_filename='{}_{}_{}'.format(printName.replace("::", "-"), fileName, elementType), image_height=imageHeight,
						image_width=imageWidth
					)

				compKeys = [x * 2 for x in range(1, len(symmetrics) + 1)]
				plot(compKeys, symmetrics, symText, "Concurrent Throughput (Symmetrical Threads) ({} <{}>)".format(printName, elementType), "Threads (1/2 consumer, 1/2 producer)", "symmetric")
				compKeys = [x * 3 for x in range(1, len(prodOverCons) + 1)]
				plot(compKeys, prodOverCons, pOCText, "Concurrent Throughput (Producer Heavy) ({} <{}>)".format(printName, elementType), "Threads (1/3 consumer, 2/3 producer)", "prod_heavy")
				compKeys = [x * 3 for x in range(1, len(conOverProds) + 1)]
				plot(compKeys, conOverProds, cOPText, "Concurrent Throughput (Consumer Heavy) ({} <{}>)".format(printName, elementType), "Threads (2/3 consumer, 1/3 producer)", "con_heavy")
				compKeys = [x * 4 for x in range(1, len(prodWayOverCons) + 1)]
				plot(compKeys, prodWayOverCons, pWOCText, "Concurrent Throughput (Very Producer Heavy) ({} <{}>)".format(printName, elementType), "Threads (1/4 consumer, 3/4 producer)", "very_prod_heavy")
				compKeys = [x * 4 for x in range(1, len(conWayOverProds) + 1)]
				plot(compKeys, conWayOverProds, cWOPText, "Concurrent Throughput (Very Consumer Heavy) ({} <{}>)".format(printName, elementType), "Threads (3/4 consumer, 1/4 producer)", "very_con_heavy")
			
for key, value in data.items():
	print_graphs(key, value, mins[key], maxes[key])

for type in types:
	if type not in symmetricData:
		continue

	dir = os.path.join("gen_html", "comp", type)
	if not os.path.exists(dir):
		os.makedirs(dir)

	annotations = [dict(
		x=1,
		y=0,
		showarrow=False,
		text="[P] = Preallocated, [ET] = Ephemeral Tickets, [NT] = No Tickets,<br>[B#] = Batch Count, [NB] = Batching Disabled",
		xref='paper',
		yref='paper',
		bgcolor=legendDetailBackground,
		bordercolor="#000000",
		yshift=-60,
		xshift=60,
		font=dict(
			family='Courier New, monospace',
			size=12,
			color='#000000'
		)
	)]
		
	typeName = '<span style="color: {};">{}</span>'.format(typeColor, type)
	layout = plotly.graph_objs.Layout(
		title = 'Raw Enqueue Throughput Comparison ({})'.format(typeName),
		xaxis = dict(
			title = 'Producer Threads',
			tickformat = ',d'
		),
		yaxis = dict(
			title = 'Throughput (op/sec)',
			#range = [0,int(allMax["enqueue"]*1.05)],
		),
		annotations=annotations,
		legend=legendAttrs,
		barmode = 'group',
		bargroupgap = 0.1,
		barcornerradius=15,
		#titlefont = titleAttrs
	)
	fig = plotly.graph_objs.Figure(
		data = enqueueData[type],
		layout = layout
	)
	plotly.offline.plot(
		fig,
		filename = os.path.join(dir, 'Enqueue_{}.html'.format(type)),
		image='png', image_filename='enqueue_{}'.format(type), image_height=imageHeight, image_width=imageWidth
	)

	#time.sleep(5)

	layout = plotly.graph_objs.Layout(
		title = 'Raw Dequeue Throughput Comparison ({})'.format(typeName),
		xaxis = dict(
			title = 'Consumer Threads',
			tickformat = ',d'
		),
		yaxis = dict(
			title = 'Throughput (op/sec)',
			#range = [0,int(allMax["dequeue"]*1.05)]
		),
		annotations=annotations,
		legend=legendAttrs,
		barmode = 'group',
		bargroupgap = 0.1,
		barcornerradius=15,
		#titlefont = titleAttrs
	)
	fig = plotly.graph_objs.Figure(
		data = dequeueData[type],
		layout = layout
	)
	plotly.offline.plot(
		fig,
		filename = os.path.join(dir, 'Dequeue_{}.html'.format(type)),
		image='png', image_filename='dequeue_{}'.format(type), image_height=imageHeight, image_width=imageWidth
	)

	#time.sleep(5)

	layout = plotly.graph_objs.Layout(
		title = 'Raw Dequeue Throughput (Empty Queue) Comparison ({})'.format(typeName),
		xaxis = dict(
			title = 'Consumer Threads',
			tickformat = ',d'
		),
		yaxis = dict(
			title = 'Throughput (op/sec)',
			#range = [0,int(allMax["deq_empty"]*1.05)]
		),
		annotations=annotations,
		legend=legendAttrs,
		barmode = 'group',
		bargroupgap = 0.1,
		barcornerradius=15,
		#titlefont = titleAttrs
	)
	fig = plotly.graph_objs.Figure(
		data = dequeueEmptyData[type],
		layout = layout
	)
	plotly.offline.plot(
		fig,
		filename = os.path.join(dir, 'Dequeue_From_Empty_{}.html'.format(type)),
		image='png', image_filename='dequeue_from_empty_{}'.format(type), image_height=imageHeight, image_width=imageWidth
	)

	#time.sleep(5)

	layout = plotly.graph_objs.Layout(
		title = 'Concurrent Throughput (Symmetrical Threads) Comparison ({})'.format(typeName),
		xaxis = dict(
			title = 'Threads (1/2 consumer, 1/2 producer)',
			tickformat = ',d',
			tickmode = "array",
			tickvals = list(range(0, 26, 2)),
			ticktext = list(range(0, 26, 2)),
		),
		yaxis = dict(
			title = 'Throughput (op/sec)',
			#range = [0,int(allMax["enq+deq"]*1.05)]
		),
		annotations=annotations,
		legend=legendAttrs,
		barmode = 'group',
		bargroupgap = 0.1,
		barcornerradius=15,
		#titlefont = titleAttrs
	)
	fig = plotly.graph_objs.Figure(
		data = symmetricData[type],
		layout = layout
	)
	plotly.offline.plot(
		fig,
		filename = os.path.join(dir, 'symmetrical_{}.html'.format(type)),
		image='png', image_filename='symmetrical_{}'.format(type), image_height=imageHeight, image_width=imageWidth
	)

	#time.sleep(5)

	layout = plotly.graph_objs.Layout(
		title = 'Concurrent Throughput (Producer Heavy) Comparison ({})'.format(typeName),
		xaxis = dict(
			title = 'Threads (1/3 consumer, 2/3 producer)',
			tickformat = ',d'
		),
		yaxis = dict(
			title = 'Throughput (op/sec)',
			#range = [0,int(allMax['enq+deq']*1.05)]
		),
		annotations=annotations,
		legend=legendAttrs,
		barmode = 'group',
		bargroupgap = 0.1,
		barcornerradius=15,
		#titlefont = titleAttrs
	)
	fig = plotly.graph_objs.Figure(
		data = prodOverConData[type],
		layout = layout
	)
	plotly.offline.plot(
		fig,
		filename = os.path.join(dir, 'prod_heavy_{}.html'.format(type)),
		image='png', image_filename='prod_heavy_{}'.format(type), image_height=imageHeight, image_width=imageWidth
	)
    
	#time.sleep(5)
    
	layout = plotly.graph_objs.Layout(
		title = 'Concurrent Throughput (Consumer Heavy) Comparison ({})'.format(typeName),
		xaxis = dict(
			title = 'Threads (2/3 consumer, 1/3 producer)',
			tickformat = ',d'
		),
		yaxis = dict(
			title = 'Throughput (op/sec)',
			#range = [0,int(allMax["enq+deq"]*1.05)]
		),
		annotations=annotations,
		legend=legendAttrs,
		barmode = 'group',
		bargroupgap = 0.1,
		barcornerradius=15,
		#titlefont = titleAttrs
	)
	fig = plotly.graph_objs.Figure(
		data = conOverProdData[type],
		layout = layout
	)
	plotly.offline.plot(
		fig,
		filename = os.path.join(dir, 'con_heavy_{}.html'.format(type)),
		image='png', image_filename='con_heavy_{}'.format(type), image_height=imageHeight, image_width=imageWidth
	)
    
	#time.sleep(5)
    
	layout = plotly.graph_objs.Layout(
		title = 'Concurrent Throughput (Very Producer Heavy) Comparison ({})'.format(typeName),
		xaxis = dict(
			title = 'Threads (1/4 consumer, 3/4 producer)',
			tickformat = ',d'
		),
		yaxis = dict(
			title = 'Throughput (op/sec)',
			#range = [0,int(allMax["enq+deq"]*1.05)]
		),
		annotations=annotations,
		legend=legendAttrs,
		barmode = 'group',
		bargroupgap = 0.1,
		barcornerradius=15,
		#titlefont = titleAttrs
	)
	fig = plotly.graph_objs.Figure(
		data = prodWayOverConData[type],
		layout = layout
	)
	plotly.offline.plot(
		fig,
		filename = os.path.join(dir, 'very_prod_heavy_{}.html'.format(type)),
		image='png', image_filename='very_prod_heavy_{}'.format(type), image_height=imageHeight, image_width=imageWidth
	)
    
	#time.sleep(5)
    
	layout = plotly.graph_objs.Layout(
		title = 'Concurrent Throughput (Very Consumer Heavy) Comparison ({})'.format(typeName),
		xaxis = dict(
			title = 'Threads (3/4 consumer, 1/4 producer)',
			tickformat = ',d'
		),
		yaxis = dict(
			title = 'Throughput (op/sec)',
			#range = [0,int(allMax["enq+deq"]*1.05)]
		),
		annotations=annotations,
		legend=legendAttrs,
		barmode = 'group',
		bargroupgap = 0.1,
		barcornerradius=15,
		#titlefont = titleAttrs
	)
	fig = plotly.graph_objs.Figure(
		data = conWayOverProdData[type],
		layout = layout
	)
	plotly.offline.plot(
		fig,
		filename = os.path.join(dir, 'very_con_heavy_{}.html'.format(type)),
		image='png', image_filename='very_con_heavy_{}'.format(type), image_height=imageHeight, image_width=imageWidth
	)

	colors = []
	for key in latencyKeys[type]:
		colors.append(lineColors[key])

	trace = plotly.graph_objs.Bar(
		x=latencyKeys[type],
		y=latencyVals[type],
		error_y=dict(
			type="data",
			symmetric=False,
			array=latencyMax[type],
			arrayminus=latencyMin[type]
		),
		hoverlabel=dict(namelength=-1),
		text=latencyTxt[type],
		marker_pattern_shape=patterns,
		marker=dict(color=colors),
	)

	layout = plotly.graph_objs.Layout(
		title = 'Latency Comparison ({}) (lower is better)'.format(typeName),
		xaxis = dict(
			title = 'Queue',
			tickformat = ',d'
		),
		yaxis = dict(
			title = 'Latency (ns)',
		),
		#annotations=annotations,
		#barmode = 'group',
		barcornerradius=15,
		#legend=legendAttrs,
		#titlefont = titleAttrs
	)
	fig = plotly.graph_objs.Figure(
		data = [trace],
		layout = layout
	)
	plotly.offline.plot(
		fig,
		filename = os.path.join(dir, 'latency_{}.html'.format(type)),
		image='png', image_filename='latency_{}'.format(type), image_height=imageHeight, image_width=imageWidth
	)

	#time.sleep(5)
