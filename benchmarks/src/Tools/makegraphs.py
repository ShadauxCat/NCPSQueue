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
parser.add_argument("--with-ranges", "-r", help="Show ranges on the line graphs", action="store_true")
parser.add_argument("--no-singles", '-n', help="Exclude results with 1 producer and 1 consumer", action="store_true")
parser.add_argument("--filter", "-f", help="Exclude types matching this regex", nargs="*", default=[])
parser.add_argument("--max", help="Make graphs of the best results (default is median)", action="store_true", default=False)
parser.add_argument("--min", help="Make graphs of the worst results (default is median)", action="store_true", default=False)
parser.add_argument("--mean", help="Make graphs of the mean results (default is median)", action="store_true", default=False)
parser.add_argument("--max-compare-cores", help="Maximum total cores to use in comparison graphs", default=24, type=int)
args = parser.parse_args()

locale.setlocale(locale.LC_ALL, '')

greyscale = args.greyscale
lineShape = "spline" if args.spline else "linear"
compOnly = args.comp_only

imageWidth = args.width
imageHeight = args.height
ranges = args.with_ranges
no_singles = args.no_singles

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
surfaceData = {}
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

markerShapes = [
	"circle", # 1024cores
	"triangle-up", 
	"triangle-down", #tbb
	"square", #boost
	"diamond", #deque
	
	"pentagon", 			
	"hexagon",				
	"cross",				
	"x",					
	"triangle-left",		
	"triangle-right",		
	
	"diamond-tall",			
	"diamond-wide",			
	"star",					
	"hexagram",				
	"star-triangle-up",		
	"star-triangle-down",	
	
	"star-square",			
	"star-diamond",			
	"hourglass",			
	"bowtie",				
]

lineColors = collections.OrderedDict()
markers = {}

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

allMax = { "1": 0, "2": 0, "3": 0, "4": 0 }
allMin = { "1": 9999999999999, "2": 9999999999999, "3": 9999999999999, "4": 9999999999999 }

maxProd = 0
maxCon = 0

types = ["char", "int64_t", "FixedStaticString"]
def get_name(id):
	return {
		"1": "Enqueue",
		"2": "Dequeue",
		"3": "Enqueue_Dequeue",
		"4": "Dequeue_From_Empty"
	}[id]

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
	try:
		split = line.split('\t')
		name = re.sub(r",(class)? std::allocator ?<.*> >", ">", split[0])
		name = re.sub(r",(class)? tbb::cache_aligned_allocator ?<.*> >", ">", name)
		
		type = split[1]
		
		elemType = GetElementType(name);
		if elemType != lastElemType:
			lastElemType = elemType
			idx = 0
		
		good = True
		for filter in args.filter:
			if filter in name:
				good = False
				break
		if not good:
			continue
		
		
		if name not in lineColors:
			lineColors[name] = visuallyDistinctColors[idx % len(visuallyDistinctColors)]
			markers[name] = markerShapes[idx % len(markerShapes)]
			idx += 1
			
		if type == '0':
			continue
			
		producers = int(split[2])
		consumers = int(split[3])
		throughput = float(split[4]) if args.mean else (float(split[6]) if args.max else (float(split[5]) if args.min else float(split[7])))
		
		skip = False
		if no_singles:
			if (producers == 1 or consumers == 1) and type == '3':
				skip = True
			elif producers == 1 and consumers == 1:
				skip = True
			
		if skip:
			throughput = None
			min_throughput = None
			max_throughput = None
		else:
			if ranges:
				min_throughput = float(split[5])
				max_throughput = float(split[6])
			else:
				min_throughput = throughput
				max_throughput = throughput
			
			if type == '3':
				maxProd = max(maxProd, producers)
				maxCon = max(maxCon, consumers)
				
			d = maxes.setdefault(name, { "1": 0, "2": 0, "3": 0, "4": 0 })
			d[type] = max(max_throughput, d[type])
			allMax[type] = max(max_throughput, allMax[type])
		
			d = mins.setdefault(name, { "1": 9999999999999, "2": 9999999999999, "3": 9999999999999, "4": 9999999999999 })
			d[type] = min(min_throughput, d[type])
			allMin[type] = min(min_throughput, allMin[type])
		
			if not ranges:
				min_throughput = None
				max_throughput = None
		
		data.setdefault(name, {}).setdefault(type, []).append((producers, consumers, throughput, min_throughput, max_throughput))
	except IndexError:
		print(line)
		raise

def intWithCommas(x):
	if x is None:
		return '';
	return locale.format("%.2f", x, grouping=True)
	

def print_graphs(name, d, minVal, maxVal):
	for type, listOfDatapoints in d.items():
		keys = []
		vals = []
		minVals = []
		maxVals = []
		sizes = []
		texts = []
		elementType = GetElementType(name)
		
		printName = name.replace("::ConcurrentQueue", "")
		printName = printName.replace("::ConcurrentBoundedQueue", "-bounded")
		printName = printName.replace("ext_", "")
		printName = printName.replace("::mpmc_bounded_queue", "")
		printName = printName.replace("::concurrent_bounded_queue", "-bounded")
		printName = printName.replace("::strict_ppl::concurrent_queue", "")
		printName = printName.replace("::lockfree::queue", "")
		printName = printName.replace("tbb::detail::d1", "tbb")
		
		printName = re.sub(r", ?true>", r">", printName)
		printName = re.sub(r", ?false>", r"> [NB]", printName)
		
		printName = re.sub(r"\[Batch \(", r"[B", printName)
		printName = re.sub(r"\)\]", r"]", printName)
		
		printName = re.sub(r"<(.+), ?8192>", r"", printName)
		printName = re.sub(r"<(.+), ?\d+>", r" [P]", printName)
		printName = re.sub("<(.+)>", r"", printName)
		
		printName = printName.replace("Ephemeral Tickets", "ET")
		printName = printName.replace("No Tickets", "NT")
		
		if (type == "1" or type == "2" or type == "4"):
			for dataPoints in listOfDatapoints:
				if type == "1":
					keys.append(dataPoints[0])
				else:
					keys.append(dataPoints[1])
				vals.append(dataPoints[2])
				minVals.append(dataPoints[3])
				maxVals.append(dataPoints[4])
				texts.append(
					"throughput: {}op/s".format(intWithCommas(dataPoints[2]))
				)
				
			trace = plotly.graph_objs.Scatter(
				x=keys,
				y=vals,
				text=texts,
				name=printName,
				mode = 'lines+markers',
				hoverlabel = dict(namelength = -1),
				line = dict(
					color = lineColors[name],#.replace('rgb', 'rgba').replace(')', ',0.25)'),
					shape = lineShape
				),
				marker = dict(
					color = lineColors[name],
					symbol = markers[name],
					size = 12
				)
			)
			
			trace2 = plotly.graph_objs.Scatter(
				x=keys + keys[::-1],
				y=maxVals + minVals[::-1],
				fill='tozerox',
				showlegend=False,
				hoverinfo='none',
				fillcolor=lineColors[name].replace('hsv', 'hsva').replace(')', ',0.1)'),
				line = dict(
					color = 'white',
					shape = lineShape
				)
			)
			#import numpy
			#model = numpy.polyfit(
			#	keys,
			#	vals,
			#	1
			#)
			#predict = numpy.poly1d(model)
			#x = 4, args.max_compare_cores
			#y = [predict(4), predict(args.max_compare_cores)]
			#trendline = plotly.graph_objs.Scatter(
			#	x=x,
			#	y=y,
			#	showlegend=False,
			#	hoverinfo='none',
			#	mode = 'lines+markers',
			#	line = dict(
			#		color = lineColors[name],
			#		shape = lineShape,
			#		dash = "dash"
			#	),
			#	marker = dict(
			#		color = lineColors[name],
			#		symbol = markers[name]+"-open",
			#		size = 12
			#	)
			#)
			
			if type == "1":
				enqueueData.setdefault(elementType, []).append(trace)
				enqueueData.setdefault(elementType, []).append(trace2)
				#enqueueData.setdefault(elementType, []).append(trendline)
			elif type == "2":
				dequeueData.setdefault(elementType, []).append(trace)
				dequeueData.setdefault(elementType, []).append(trace2)
				#dequeueData.setdefault(elementType, []).append(trendline)
			else:
				dequeueEmptyData.setdefault(elementType, []).append(trace)
				dequeueEmptyData.setdefault(elementType, []).append(trace2)
				#dequeueEmptyData.setdefault(elementType, []).append(trendline)
		elif type == "3":
			colors = []
			global heatmap
			heatmap = []
			heatmaptxt = []
			
			symmetrics = []
			symMax = []
			symMin = []
			prodOverCons = []
			pOCMax = []
			pOCMin = []
			conOverProds = []
			cOPMax = []
			cOPMin = []
			prodWayOverCons = []
			pWOCMax = []
			pWOCMin = []
			conWayOverProds = []
			cWOPMax = []
			cWOPMin = []
			for dataPoints in listOfDatapoints:		

				if dataPoints[0] + dataPoints[1] <= args.max_compare_cores:			
					if dataPoints[0] == dataPoints[1]:
						symmetrics.append(dataPoints[2])
						symMin.append(dataPoints[3])
						symMax.append(dataPoints[4])
					elif dataPoints[0] == dataPoints[1] * 2:
						prodOverCons.append(dataPoints[2])
						pOCMin.append(dataPoints[3])
						pOCMax.append(dataPoints[4])
					elif dataPoints[0] * 2 == dataPoints[1]:
						conOverProds.append(dataPoints[2])
						cOPMax.append(dataPoints[3])
						cOPMin.append(dataPoints[4])
					elif dataPoints[0] == dataPoints[1] * 3:
						prodWayOverCons.append(dataPoints[2])
						pWOCMin.append(dataPoints[3])
						pWOCMax.append(dataPoints[4])
					elif dataPoints[0] * 3 == dataPoints[1]:
						conWayOverProds.append(dataPoints[2])
						cWOPMax.append(dataPoints[3])
						cWOPMin.append(dataPoints[4])
				
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
			trace = plotly.graph_objs.Scatter(
				x=compKeys,
				y=symmetrics,
				name=printName,
				hoverlabel = dict(namelength = -1),
				mode = 'lines+markers',
				line = dict(
					color = lineColors[name],#.replace('rgb', 'rgba').replace(')', ',0.25)'),
					shape = lineShape
				),
				marker = dict(
					color = lineColors[name],
					symbol = markers[name],
					size = 12
				)
			)
			trace2 = plotly.graph_objs.Scatter(
				x=compKeys + compKeys[::-1],
				y=symMax + symMin[::-1],
				fill='tozerox',
				showlegend=False,
				hoverinfo='none',
				fillcolor=lineColors[name].replace('hsv', 'hsva').replace(')', ',0.1)'),
				line = dict(
					color = 'white',
					shape = lineShape
				)
			)
			import numpy
			model = numpy.polyfit(
				compKeys[1:] if no_singles else compKeys,
				symmetrics[1:] if no_singles else compKeys,
				1
			)
			predict = numpy.poly1d(model)
			x = 4, args.max_compare_cores
			y = [predict(4), predict(args.max_compare_cores)]
			trendline = plotly.graph_objs.Scatter(
				x=x,
				y=y,
				showlegend=False,
				hoverinfo='none',
				mode = 'lines+markers',
				line = dict(
					color = lineColors[name],
					shape = lineShape,
					dash = "dash"
				),
				marker = dict(
					color = lineColors[name],
					symbol = markers[name]+"-open",
					size = 12
				)
			)
			symmetricData.setdefault(elementType, []).extend([trace, trace2])
			
			compKeys = [x*3 for x in range(1,len(prodOverCons)+1)]
			trace = plotly.graph_objs.Scatter(
				x=compKeys,
				y=prodOverCons,
				name=printName,
				hoverlabel = dict(namelength = -1),
				mode = 'lines+markers',
				line = dict(
					color = lineColors[name],
					shape = lineShape
				),
				marker = dict(
					symbol = markers[name],
					size = 12
				)

			)
			trace2 = plotly.graph_objs.Scatter(
				x=compKeys + compKeys[::-1],
				y=pOCMax + pOCMin[::-1],
				fill='tozerox',
				showlegend=False,
				hoverinfo='none',
				fillcolor=lineColors[name].replace('hsv', 'hsva').replace(')', ',0.1)'),
				line = dict(
					color = 'white',
					shape = lineShape
				)
			)
			prodOverConData.setdefault(elementType, []).extend([trace, trace2])
			
			compKeys = [x*3 for x in range(1,len(conOverProds)+1)]
			trace = plotly.graph_objs.Scatter(
				x=compKeys,
				y=conOverProds,
				name=printName,
				hoverlabel = dict(namelength = -1),
				mode = 'lines+markers',
				line = dict(
					color = lineColors[name],
					shape = lineShape
				),
				marker = dict(
					symbol = markers[name],
					size = 12
				)
			)
			trace2 = plotly.graph_objs.Scatter(
				x=compKeys + compKeys[::-1],
				y=cOPMax + cOPMin[::-1],
				fill='tozerox',
				showlegend=False,
				hoverinfo='none',
				fillcolor=lineColors[name].replace('hsv', 'hsva').replace(')', ',0.1)'),
				line = dict(
					color = 'white',
					shape = lineShape
				)
			)
			conOverProdData.setdefault(elementType, []).extend([trace, trace2])
			
			compKeys = [x*4 for x in range(1,len(prodWayOverCons)+1)]
			trace = plotly.graph_objs.Scatter(
				x=compKeys,
				y=prodWayOverCons,
				name=printName,
				hoverlabel = dict(namelength = -1),
				mode = 'lines+markers',
				line = dict(
					color = lineColors[name],
					shape = lineShape
				),
				marker = dict(
					symbol = markers[name],
					size = 12
				)
			)
			trace2 = plotly.graph_objs.Scatter(
				x=compKeys + compKeys[::-1],
				y=pWOCMax + pWOCMin[::-1],
				fill='tozerox',
				showlegend=False,
				hoverinfo='none',
				fillcolor=lineColors[name].replace('hsv', 'hsva').replace(')', ',0.1)'),
				line = dict(
					color = 'white',
					shape = lineShape
				)
			)
			prodWayOverConData.setdefault(elementType, []).extend([trace, trace2])
			
			compKeys = [x*4 for x in range(1,len(conWayOverProds)+1)]
			trace = plotly.graph_objs.Scatter(
				x=compKeys,
				y=conWayOverProds,
				name=printName,
				hoverlabel = dict(namelength = -1),
				mode = 'lines+markers',
				line = dict(
					color = lineColors[name],
					shape = lineShape
				),
				marker = dict(
					symbol = markers[name],
					size = 12
				)
			)
			trace2 = plotly.graph_objs.Scatter(
				x=compKeys + compKeys[::-1],
				y=cWOPMax + cWOPMin[::-1],
				fill='tozerox',
				showlegend=False,
				hoverinfo='none',
				fillcolor=lineColors[name].replace('hsv', 'hsva').replace(')', ',0.1)'),
				line = dict(
					color = 'white',
					shape = lineShape
				)
			)
			conWayOverProdData.setdefault(elementType, []).extend([trace, trace2])

			trace = plotly.graph_objs.Scatter(
				x=keys,
				y=vals,
				mode='markers',
				text=texts,
				marker=dict(
					size=sizes,
					line = dict(
						width = 2,
						color = 'rgb(0, 0, 0)'
					),
					color = colors + [0, allMax[type]],
					colorscale=colorscale,
					showscale=True
				),
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
					tickformat = ',d'
				),
				yaxis = dict(
					title = 'Consumer Threads',
					tickformat = ',d'
				),
				hovermode = 'closest',
				showlegend = False,
				titlefont = titleAttrs
			)
			
			dir = os.path.join(get_name(type), elementType)
			if not os.path.exists(dir):
				os.makedirs(dir)
				
			fig = plotly.graph_objs.Figure(
				data = data,
				layout = layout
			)
			if not compOnly:
				plotly.offline.plot(
					fig,
					filename = os.path.join(dir, printName.replace("::", "-") + "_" + get_name(type) + '.html'),
					image='png', image_filename=printName.replace("::", "-") + "_" + elementType, image_height=imageHeight, image_width=imageWidth
				)
			
			heatmap[0] = [None] * len(heatmap[1])
			
			trace = plotly.graph_objs.Heatmap(
				z = heatmap,
				text=heatmaptxt,
				colorscale=colorscale,
				zsmooth='best',
				zmin=0,
				zmax=allMax[type],
			)
			
			data = [trace, trace2]
			layout = plotly.graph_objs.Layout(
				title = '{}<br>min: {}op/s<br>max: {}op/s'.format(
					printName, intWithCommas(mins[name][type]), intWithCommas(maxes[name][type])
				),
				xaxis = dict(
					title = 'Producer Threads',
					range = [0.5,len(heatmap) - 1],
					tickformat = ',d'
				),
				yaxis = dict(
					title = 'Consumer Threads',
					range = [0.5,len(heatmap[1]) - 1],
					tickformat = ',d'
				),
				hovermode = 'closest',
				titlefont = titleAttrs
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
			
			trace = plotly.graph_objs.Surface(
				z = heatmap,
				colorscale=colorscale,
				cmin=0,
				cmax=allMax[type],
				cauto=False
			)
			
			flatColorTrace = plotly.graph_objs.Surface(
				z = heatmap,
				name=printName,
				hoverlabel = dict(namelength = -1),
				colorscale=[(i/10.0, lineColors[name]) for i in range(0,11)],
				cmin=-0.5,
				cmax=0.5,
				showscale=False,
				cauto=False
			)
			
			data = [trace]
			surfaceData.setdefault(elementType, []).append(flatColorTrace)
			
			layout = plotly.graph_objs.Layout(
				title = '{}<br>min: {}op/s<br>max: {}op/s'.format(
					printName, intWithCommas(mins[name][type]), intWithCommas(maxes[name][type])
				),
				scene = dict(
					xaxis = dict(
						title = 'Producer Threads',
						range = [1,len(heatmap) - 1],
						tickformat = ',d'
					),
					yaxis = dict(
						title = 'Consumer Threads',
						range = [1,len(heatmap[1]) - 1],
						tickformat = ',d'
					),
					zaxis = dict(
						title = 'Throughput (op/s)',
						range = [0,allMax[type]]
					),
					camera = dict(
						eye = dict(
							x = 1.5,
							y = 1.5,
							z = 1,
						)
					),
				),
				hovermode = 'closest',
				titlefont = titleAttrs
			)
			fig = plotly.graph_objs.Figure(
				data = data,
				layout = layout
			)
			if not compOnly:
				plotly.offline.plot(
					fig,
					filename = os.path.join(dir, printName.replace("::", "-") + "_" + get_name(type) + '_surface.html'),
				#	image='png', image_filename=name.replace(":", "_").replace("<", "_").replace(">", "_") + '_surface', image_height=imageHeight, image_width=imageWidth
				)
				#time.sleep(5)
			
for key, value in data.items():
	print_graphs(key, value, mins[key], maxes[key])

for type in types:
	if type not in symmetricData:
		continue
		
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
			#range = [0,int(allMax['1']*1.05)],
		),
		annotations=annotations,
		legend=legendAttrs,
		titlefont = titleAttrs
	)
	fig = plotly.graph_objs.Figure(
		data = enqueueData[type],
		layout = layout
	)
	plotly.offline.plot(
		fig,
		filename = 'Enqueue_{}.html'.format(type),
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
			#range = [0,int(allMax['2']*1.05)]
		),
		annotations=annotations,
		legend=legendAttrs,
		titlefont = titleAttrs
	)
	fig = plotly.graph_objs.Figure(
		data = dequeueData[type],
		layout = layout
	)
	plotly.offline.plot(
		fig,
		filename = 'Dequeue_{}.html'.format(type),
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
			#range = [0,int(allMax['4']*1.05)]
		),
		annotations=annotations,
		legend=legendAttrs,
		titlefont = titleAttrs
	)
	fig = plotly.graph_objs.Figure(
		data = dequeueEmptyData[type],
		layout = layout
	)
	plotly.offline.plot(
		fig,
		filename = 'Dequeue_From_Empty_{}.html'.format(type),
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
			#range = [0,int(allMax['3']*1.05)]
		),
		annotations=annotations,
		legend=legendAttrs,
		titlefont = titleAttrs
	)
	fig = plotly.graph_objs.Figure(
		data = symmetricData[type],
		layout = layout
	)
	plotly.offline.plot(
		fig,
		filename = 'symmetrical_{}.html'.format(type),
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
			range = [0,int(allMax['3']*1.05)]
		),
		annotations=annotations,
		legend=legendAttrs,
		titlefont = titleAttrs
	)
	fig = plotly.graph_objs.Figure(
		data = prodOverConData[type],
		layout = layout
	)
	plotly.offline.plot(
		fig,
		filename = 'prod_heavy_{}.html'.format(type),
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
			range = [0,int(allMax['3']*1.05)]
		),
		annotations=annotations,
		legend=legendAttrs,
		titlefont = titleAttrs
	)
	fig = plotly.graph_objs.Figure(
		data = conOverProdData[type],
		layout = layout
	)
	plotly.offline.plot(
		fig,
		filename = 'con_heavy_{}.html'.format(type),
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
			range = [0,int(allMax['3']*1.05)]
		),
		annotations=annotations,
		legend=legendAttrs,
		titlefont = titleAttrs
	)
	fig = plotly.graph_objs.Figure(
		data = prodWayOverConData[type],
		layout = layout
	)
	plotly.offline.plot(
		fig,
		filename = 'very_prod_heavy_{}.html'.format(type),
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
			range = [0,int(allMax['3']*1.05)]
		),
		annotations=annotations,
		legend=legendAttrs,
		titlefont = titleAttrs
	)
	fig = plotly.graph_objs.Figure(
		data = conWayOverProdData[type],
		layout = layout
	)
	plotly.offline.plot(
		fig,
		filename = 'very_con_heavy_{}.html'.format(type),
		image='png', image_filename='very_con_heavy_{}'.format(type), image_height=imageHeight, image_width=imageWidth
	)

	#time.sleep(5)

	annotations = []
	offset = 0
	for name, color in lineColors.items():
		if GetElementType(name) != type:
			continue
		
		printName = name.replace("::ConcurrentQueue", "")
		printName = printName.replace("::ConcurrentBoundedQueue", "-bounded")
		printName = printName.replace("ext_", "")
		printName = printName.replace("::mpmc_bounded_queue", "")
		printName = printName.replace("::concurrent_bounded_queue", "-bounded")
		printName = printName.replace("::strict_ppl::concurrent_queue", "")
		printName = printName.replace("::lockfree::queue", "")
		printName = printName.replace("tbb::detail::d1", "tbb")
		
		printName = re.sub(r", ?true>", r">", printName)
		printName = re.sub(r", ?false>", r"> [NB]", printName)
		
		printName = re.sub(r"\[Batch \(", r"[B", printName)
		printName = re.sub(r"\)\]", r"]", printName)
		
		printName = re.sub(r"<(.+), ?8192>", r"", printName)
		printName = re.sub(r"<(.+), ?\d+>", r" [P]", printName)
		printName = re.sub("<(.+)>", r"", printName)
		
		printName = printName.replace("Ephemeral Tickets", "ET")
		printName = printName.replace("No Tickets", "NT")
		
		annotations.append(dict(
			x=1,
			y=1,
			showarrow=False,
			text=printName,
			xref='paper',
			yref='paper',
			bgcolor=color,
			bordercolor="#000000",
			yshift=offset,
			font=dict(
				family='Courier New, monospace',
				size=16,
				color='#ffffff'
			)
		))
		offset -= 20

	layout = plotly.graph_objs.Layout(
		title = 'Concurrent Performance Comparison ({})<br>min: {}op/s<br>max: {}op/s'.format(
			typeName, intWithCommas(mins[name]['3']), intWithCommas(maxes[name]['3'])
		),
		scene = dict(
			xaxis = dict(
				title = 'Producer Threads',
				range = [1,len(heatmap) - 1],
				tickformat = ',d'
			),
			yaxis = dict(
				title = 'Consumer Threads',
				range = [1,len(heatmap[1]) - 1],
				tickformat = ',d'
			),
			zaxis = dict(
				title = 'Throughput (op/s)'
			),
			camera = dict(
				eye = dict(
					x = 1.5,
					y = 1.5,
					z = 1,
				)
			),
		),
		annotations=annotations,
		hovermode = 'closest',
		titlefont = titleAttrs
	)
	fig = plotly.graph_objs.Figure(
		data = surfaceData[type],
		layout = layout
	)
	plotly.offline.plot(
		fig,
		filename = 'compare_surface_{}.html'.format(type),
		#image='png', image_filename='compare_surface_{}'.format(type), image_height=imageHeight, image_width=imageWidth
	)