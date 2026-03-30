# Copyright (C) 2016 Jaedyn K. Draper
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
.. module:: perf_timer
	:synopsis: Thread-safe performance timer to collect high-level performance statistics

.. moduleauthor:: Jaedyn K. Draper
"""

from __future__ import unicode_literals, division, print_function

import time
import threading
import re
import math
import sys
import os

from collections import deque
_collecting = True

class ReportMode(object):
	"""
	Enum defining the perf timer reporting mode.
	"""
	TREE = 0
	FLAT = 1
	HTML = 2

def EnablePerfTracking(enable=True):
	"""
	Enable (or disable) the perf timer.

	:param enable: True to enable the perf timer, False to disable.
	:type enable: bool
	"""
	global _collecting
	_collecting = enable

def DisablePerfTracking():
	"""
	Helper function for explicitly disabling the perf timer.
	"""
	EnablePerfTracking(False)

_htmlHeader = """<!DOCTYPE html><HTML>
	<HEAD>
		<title>Perf report for {0}</title>
		<script type="text/javascript">
			var scriptLoaded = false;
			function checkScriptLoaded() {{
				if (!scriptLoaded) {{
					document.getElementById("errorbar").innerHTML="Could not contact gstatic.com to access google charts API.Tree maps will not be available until connection is restored.";
				}}
			}}
			function _width(s, w) {{
				s = "0000" + s
				return s.substring(s.length - w)
			}}

			function _formatTime(totaltime){{
				totalmin = Math.floor(totaltime / 60)
				totalsec = Math.floor(totaltime % 60)
				msec = Math.floor((totaltime - Math.floor(totaltime))*10000)
				return totalmin + ":" + _width(totalsec, 2) + "." + _width(msec, 4)
			}}
		</script>
		<style>
			.hoversort {{
			 	cursor: pointer; cursor: hand;
			}}
			.hoversort:hover{{
				color:blue;
			}}
			.percentbar {{
				height:22px;
				background-color:#a060ff;
				margin-top:-22px;

			}}

			.gradient {{
				background: rgba(235,233,249,1);
				background: -moz-linear-gradient(top, rgba(235,233,249,1) 0%, rgba(216,208,239,1) 50%, rgba(206,199,236,1) 51%, rgba(193,191,234,1) 100%);
				background: -webkit-gradient(left top, left bottom, color-stop(0%, rgba(235,233,249,1)), color-stop(50%, rgba(216,208,239,1)), color-stop(51%, rgba(206,199,236,1)), color-stop(100%, rgba(193,191,234,1)));
				background: -webkit-linear-gradient(top, rgba(235,233,249,1) 0%, rgba(216,208,239,1) 50%, rgba(206,199,236,1) 51%, rgba(193,191,234,1) 100%);
				background: -o-linear-gradient(top, rgba(235,233,249,1) 0%, rgba(216,208,239,1) 50%, rgba(206,199,236,1) 51%, rgba(193,191,234,1) 100%);
				background: -ms-linear-gradient(top, rgba(235,233,249,1) 0%, rgba(216,208,239,1) 50%, rgba(206,199,236,1) 51%, rgba(193,191,234,1) 100%);
				background: linear-gradient(to bottom, rgba(235,233,249,1) 0%, rgba(216,208,239,1) 50%, rgba(206,199,236,1) 51%, rgba(193,191,234,1) 100%);
				filter: progid:DXImageTransform.Microsoft.gradient( startColorstr='#ebe9f9', endColorstr='#c1bfea', GradientType=0 );
			}}
		</style>
	</HEAD>
	<BODY onload="checkScriptLoaded()">
		<div id="errorbar" style="background-color:#ff0000"></div>
		<script type="text/javascript" src="https://www.gstatic.com/charts/loader.js" onload="scriptLoaded=true;" ></script>
		<h1>Perf Report: <i>{0}</i></h1>
"""

_blocks = [
"""		<div style="margin:2px 10px;padding: 5px 10px;background-color:lavender;border: 1px solid grey;">
			<h3>{1}</h3>

			<div id="chart_div_{0}"></div>
			<script type="text/javascript">
				google.charts.load("current", {{"packages":["treemap"]}});
				google.charts.setOnLoadCallback(drawChart);
				function drawChart() {{
					var data = new google.visualization.DataTable();
					data.addColumn("string", "ID");
					data.addColumn("string", "Parent");
					data.addColumn("number", "Exclusive Time in Seconds");
					data.addColumn("number", "Inclusive time in seconds");
					data.addRows([
""",
"""					]);
					var tree = new google.visualization.TreeMap(document.getElementById("chart_div_{0}"));
					function showFullTooltip(row, size, value) {{
						return '<div style="background:#fd9; padding:10px; border-style:solid">' +
						'<span style="font-family:Courier"><b>' +
						data.getValue(row, 0).split("\x0b").join("").split("<").join("&lt;").split(">").join("&gt;")
						+ ':</b>' + _formatTime(data.getValue(row, 2)) + ' seconds</span></div>'
					}}
					var options = {{
						highlightOnMouseOver: true,
						maxDepth: 1,
						maxPostDepth: 20,
						minHighlightColor: "#80a0ff",
						midHighlightColor: "#ffffff",
						maxHighlightColor: "#ff0000",
						minColor: "#7390E6",
						midColor: "#E6E6E6",
						maxColor: "#e60000",
						headerHeight: 15,
						showScale: false,
						height: 500,
						useWeightedAverageForAggregation: true,
						generateTooltip: showFullTooltip
					}};
					tree.draw(data, options);
				}}
			</script>
			<script type="text/javascript">
				var datas_{0} = [
""",
"""				function HideChildren_{0}(parentId) {{
						className = '{0}_Parent_' + parentId
						elems = document.getElementsByClassName(className)
						arrowElem = document.getElementById("arrow_{0}_"+parentId)
						for(var i = 0; i < elems.length; ++i) {{
							var elem = elems[i]
							if(elem.style.maxHeight == '0px') {{
								elem.style.maxHeight=elem.rememberMaxHeight
								arrowElem.innerHTML = '&#x25bc;'
							}}
							else
							{{
								elem.style.maxHeight='0px'
								arrowElem.innerHTML = '&#x25b6;'
							}}
						}}
					}}

					var mode_{0} = "tree"

					function Flatten_{0}() {{
						ret = {{}}
						function recurse(datas) {{
							if(datas.length == 0) {{
								return;
							}}
							for(var i = 0; i < datas.length; ++i) {{
								if(datas[i][0] in ret) {{
									item = ret[datas[i][0]]
									item[0] += datas[i][1]
									item[1] += datas[i][2]
									item[2] += datas[i][3]
									item[3] += datas[i][4]
									item[4] += datas[i][5]
									item[5] += datas[i][6]
									item[6] += datas[i][7]
									item[7] += datas[i][8]
									item[8] += datas[i][9]
								}}
								else {{
									ret[datas[i][0]] = [
										datas[i][1],
										datas[i][2],
										datas[i][3],
										datas[i][4],
										datas[i][5],
										datas[i][6],
										datas[i][7],
										datas[i][8],
										datas[i][9]
									];
								}}
								recurse(datas[i][10]);
							}}
						}}
						recurse(datas_{0});
						retArray = []
						for(var key in ret) {{
							item = ret[key]
							retArray.push([
								key,
								item[0],
								item[1],
								item[2],
								item[3],
								item[4],
								item[5],
								item[6],
								item[7],
								item[8],
								[]
							]);
						}}
						return retArray;
					}}

					var prevSortKey_{0} = 1
					var prevSortType_{0} = -1
					var maxId_{0} = -1
					function Populate_{0}(sortKey) {{
						var sortType = 1
						if(sortKey == 0) {{
							sortType = -1
						}}
						if(prevSortKey_{0} == sortKey && prevSortType_{0} == sortType) {{
							sortType *= -1
						}}
						prevSortKey_{0} = sortKey
						prevSortType_{0} = sortType

						elem = document.getElementById("stack_{0}")
						bg1 = "#DFDFF2"
						bg2 = "#D3D3E6"
						var s = '<div style="border:1px solid black"><div style="font-weight:bold;border-bottom:1px solid black;" class="gradient">'
						s += '<span class="hoversort" style="width:37%;display:inline-block;text-align:center;" onclick="Populate_{0}(0)">Block</span>'
						s += '<span class="hoversort" style="width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;" onclick="Populate_{0}(1)">Inclusive</span>'
						s += '<span class="hoversort" style="width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;" onclick="Populate_{0}(2)">Exclusive</span>'
						s += '<span class="hoversort" style="width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;" onclick="Populate_{0}(3)">Count</span>'
						s += '<span class="hoversort" style="width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;" onclick="Populate_{0}(4)">Inclusive Max</span>'
						s += '<span class="hoversort" style="width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;" onclick="Populate_{0}(5)">Inclusive Min</span>'
						s += '<span class="hoversort" style="width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;" onclick="Populate_{0}(6)">Inclusive Mean</span>'
						s += '<span class="hoversort" style="width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;" onclick="Populate_{0}(7)">Exclusive Max</span>'
						s += '<span class="hoversort" style="width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;" onclick="Populate_{0}(8)">Exclusive Min</span>'
						s += '<span class="hoversort" style="width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;" onclick="Populate_{0}(9)">Exclusive Mean</span>'
						s += '</div>'
						var id = 1
						function recurse(oneLevel, depth, parentId) {{
							oneLevel = oneLevel.sort(function(a, b) {{
								var x = a[sortKey]; var y = b[sortKey];
								return ((x < y) ? 1 : ((x > y) ? -1 : 0)) * sortType;
							}});
							for(var i=0; i < oneLevel.length; ++i) {{
								var thisId = id;
								id += 1;
								if(thisId %2 == 0) {{
									bg1 = "#C8C6F2"
									bg2 = "#B3B1D9"
								}}
								else {{
									bg1 = "#BDBBE6"
									bg2 = "#A8A7CC"
								}}
								s += '<div style="width:100%;overflow:hidden;transition:max-height 0.5s linear" class="{0}_Parent_'+parentId+'", id="{0}_'+thisId+'">'
								s += '<div style="line-height:22px;"><span style="height:100%;width:37%;display:inline-block;background-color:'+bg1+'" '
								if(oneLevel[i][10].length != 0) {{
									s += 'class="hoversort" onclick="HideChildren_{0}(\\''+thisId+'\\')"'
								}}
								s += '><span style="width:20px;display:inline-block;margin-left:' + (depth * 15) + 'px;" id="arrow_{0}_'+thisId+'">'
								if(oneLevel[i][10].length != 0) {{
									s += '&#x25bc;'
								}}
								s += '</span>' + oneLevel[i][0] + '</span>'
								s += '<span style="height:100%;width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;background-color:'+bg2+'">' + _formatTime(oneLevel[i][1])
								s += '<div class="percentbar", style="width:' + Math.min(100,oneLevel[i][1]/totals_{0}[0] * 100) + '%;"></div>'
								s += '</span>'
								s += '<span style="height:100%;width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;background-color:'+bg1+'">' + _formatTime(oneLevel[i][2])
								s += '<div class="percentbar", style="width:' + Math.min(100,oneLevel[i][2]/totals_{0}[0] * 100) + '%;"></div>'
								s += '</span>'
								s += '<span style="height:100%;width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;background-color:'+bg2+'">' + oneLevel[i][3]
								s += '<div class="percentbar", style="width:' + Math.min(100,oneLevel[i][3]/totals_{0}[1] * 100) + '%;"></div>'
								s += '</span>'
								s += '<span style="height:100%;width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;background-color:'+bg1+'">' + _formatTime(oneLevel[i][4])
								s += '<div class="percentbar", style="width:' + Math.min(100,oneLevel[i][4]/totals_{0}[2] * 100) + '%;"></div>'
								s += '</span>'
								s += '<span style="height:100%;width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;background-color:'+bg2+'">' + _formatTime(oneLevel[i][5])
								s += '<div class="percentbar", style="width:' + Math.min(100,oneLevel[i][5]/totals_{0}[3] * 100) + '%;"></div>'
								s += '</span>'
								s += '<span style="height:100%;width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;background-color:'+bg2+'">' + _formatTime(oneLevel[i][6])
								s += '<div class="percentbar", style="width:' + Math.min(100,oneLevel[i][6]/totals_{0}[4] * 100) + '%;"></div>'
								s += '</span>'
								s += '<span style="height:100%;width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;background-color:'+bg2+'">' + _formatTime(oneLevel[i][7])
								s += '<div class="percentbar", style="width:' + Math.min(100,oneLevel[i][7]/totals_{0}[5] * 100) + '%;"></div>'
								s += '</span>'
								s += '<span style="height:100%;width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;background-color:'+bg2+'">' + _formatTime(oneLevel[i][8])
								s += '<div class="percentbar", style="width:' + Math.min(100,oneLevel[i][8]/totals_{0}[6] * 100) + '%;"></div>'
								s += '</span>'
								s += '<span style="height:100%;width:7%;display:inline-block;border-left:1px solid black;margin-left:-1px;text-align:center;background-color:'+bg2+'">' + _formatTime(oneLevel[i][9])
								s += '<div class="percentbar", style="width:' + Math.min(100,oneLevel[i][9]/totals_{0}[7] * 100) + '%;"></div>'
								s += '</span></div>'
								recurse(oneLevel[i][10], depth + 1, thisId)
								s += "</div>"
							}}
						}}
						var datas;
						if(mode_{0} == "flat") {{
							datas = Flatten_{0}();
						}}
						else {{
							datas = datas_{0};
						}}
						recurse(datas, 0, 0)
						s += '</div>'
						elem.innerHTML = s
						for(var i = 0; i < id; ++i) {{
							className = '{0}_Parent_' + i
							elems = document.getElementsByClassName(className)
							for(var j = 0; j < elems.length; ++j) {{
								var elem = elems[j]
								elem.style.maxHeight = Math.max(22, elem.clientHeight) + "px"
								elem.rememberMaxHeight = elem.style.maxHeight
							}}
						}}
						maxId_{0} = id
					}}

					function ExpandAll_{0}() {{
						for(var i = 1; i < maxId_{0}; ++i) {{
							className = '{0}_Parent_' + i
							elems = document.getElementsByClassName(className)
							arrowElem = document.getElementById("arrow_{0}_"+i)
							for(var j = 0; j < elems.length; ++j) {{
								var elem = elems[j]
								elem.style.maxHeight=elem.rememberMaxHeight
								arrowElem.innerHTML = '&#x25bc;'
							}}
						}}
						return false;
					}}

					function CollapseAll_{0}() {{
						for(var i = 1; i < maxId_{0}; ++i) {{
							className = '{0}_Parent_' + i
							elems = document.getElementsByClassName(className)
							arrowElem = document.getElementById("arrow_{0}_"+i)
							for(var j = 0; j < elems.length; ++j) {{
								var elem = elems[j]
								elem.style.maxHeight='0px'
								arrowElem.innerHTML = '&#x25b6;'
							}}
						}}
						return false;
					}}

					function RenderTreeView_{0}() {{
						if(mode_{0} != "tree") {{
							mode_{0} = "tree";
							prevSortType_{0} *= -1
							Populate_{0}(prevSortKey_{0})
							elem = document.getElementById("expandcollapse_{0}")
							elem.style.opacity = 100
							elem.style.visibility = "visible"
						}}
						return false;
					}}

					function RenderFlatView_{0}() {{
						if(mode_{0} != "flat") {{
							mode_{0} = "flat";
							prevSortType_{0} *= -1
							Populate_{0}(prevSortKey_{0})
							elem = document.getElementById("expandcollapse_{0}")
							elem.style.opacity = 0
							elem.style.visibility = "hidden"
						}}
						return false;
					}}

			</script>
			<div>
			<div style="border:1px solid black;padding:0px 6px">
				<div style="float:left;transition:opacity 0.5s, visibility 0.5s" id="expandcollapse_{0}">
					<a href="javascript:;" onclick="ExpandAll_{0}()">expand all</a> |
					<a href="javascript:;" onclick="CollapseAll_{0}()">collapse all</a>
				</div>
				&nbsp;
				<div style="float:right">
					View as:
					<a href="javascript:;" onclick="RenderTreeView_{0}()">tree</a> |
					<a href="javascript:;" onclick="RenderFlatView_{0}()">flat</a>
				</div>
			</div>
			<div style="clear:left" id="stack_{0}"></div>
			</div>
			<script type="text/javascript">Populate_{0}(1);</script>
		</div>
"""
]

_htmlFooter = """	</BODY>
</HTML>"""


def _formatTime(totaltime):
	totalmin = math.floor(totaltime / 60)
	totalsec = math.floor(totaltime % 60)
	msec = math.floor((totaltime - math.floor(totaltime))*10000)
	return "{}:{:02}.{:04}".format(int(totalmin), int(totalsec), int(msec))

class PerfTimer(object):
	"""
	Performance timer to collect performance stats on csbuild to aid in diagnosing slow builds.
	Used as a context manager around a block of code, will store cumulative execution time for that block.

	:param blockName: The name of the block to store execution for.
	:type blockName: str
	"""
	perfQueue = deque()
	perfStack = threading.local()

	def __init__(self, blockName):
		if _collecting:
			self.blockName = blockName
			self.incstart = 0
			self.excstart = 0
			self.exclusive = 0
			self.inclusive = 0
			self.scopeName = blockName

	def __enter__(self):
		if _collecting:
			now = time.time()
			try:
				prev = PerfTimer.perfStack.stack[-1]
				prev.exclusive += now - prev.excstart
				self.scopeName = prev.scopeName + "::" + self.blockName

				PerfTimer.perfStack.stack.append(self)
			except:
				PerfTimer.perfStack.stack = [self]

			self.incstart = now
			self.excstart = now

	def __exit__(self, excType, excVal, excTb):
		if _collecting:
			now = time.time()
			try:
				prev = PerfTimer.perfStack.stack[-2]
				prev.excstart = now
			except:
				pass

			self.exclusive += now - self.excstart
			self.inclusive = now - self.incstart

			PerfTimer.perfQueue.append((self.scopeName, self.inclusive, self.exclusive, threading.current_thread().ident))
			PerfTimer.perfStack.stack.pop()

	@staticmethod
	def PrintPerfReport(reportMode, output=None):
		"""
		Print out all the collected data from PerfTimers in a heirarchical tree

		:param reportMode: :class:`ReportMode` enum value defining how the report is output to the user.
		:type reportMode: int

		:param output: When the report mode is "flat" or "tree, this is a function that receives each line of output (defaults to stdout when None).
		               When the report mode is "html", this is the name of the file dumped by the report (defaults to the name of the main module file + "_PERF.html" when None).
		:type output: None or :class:`collections.Callable` or str
		"""

		fullreport = {}
		threadreports = {}

		#pylint: disable=missing-docstring
		class Position(object):
			Inclusive = 0
			Exclusive = 1
			Count = 2
			MaxInc = 3
			MaxExc = 4
			MinInc = 5
			MinExc = 6

		while True:
			try:
				pair = PerfTimer.perfQueue.popleft()
				if reportMode == ReportMode.FLAT:
					split = pair[0].rsplit("::", 1)
					if len(split) == 2:
						key = split[1]
					else:
						key = split[0]
					pair = (
						key,
						pair[1],
						pair[2],
						pair[3]
					)

				fullreport.setdefault(pair[0], [0,0,0,0,0,999999999,999999999])
				fullreport[pair[0]][Position.Inclusive] += pair[1]
				fullreport[pair[0]][Position.Exclusive] += pair[2]
				fullreport[pair[0]][Position.Count] += 1
				fullreport[pair[0]][Position.MaxInc] = max(pair[1], fullreport[pair[0]][Position.MaxInc])
				fullreport[pair[0]][Position.MaxExc] = max(pair[2], fullreport[pair[0]][Position.MaxExc])
				fullreport[pair[0]][Position.MinInc] = min(pair[1], fullreport[pair[0]][Position.MinInc])
				fullreport[pair[0]][Position.MinExc] = min(pair[2], fullreport[pair[0]][Position.MinExc])

				threadreport = threadreports.setdefault(pair[3], {})
				threadreport.setdefault(pair[0], [0,0,0,0,0,999999999,999999999])
				threadreport[pair[0]][Position.Inclusive] += pair[1]
				threadreport[pair[0]][Position.Exclusive] += pair[2]
				threadreport[pair[0]][Position.Count] += 1
				threadreport[pair[0]][Position.MaxInc] = max(pair[1], threadreport[pair[0]][Position.MaxInc])
				threadreport[pair[0]][Position.MaxExc] = max(pair[2], threadreport[pair[0]][Position.MaxExc])
				threadreport[pair[0]][Position.MinInc] = min(pair[1], threadreport[pair[0]][Position.MinInc])
				threadreport[pair[0]][Position.MinExc] = min(pair[2], threadreport[pair[0]][Position.MinExc])
			except IndexError:
				break

		if not fullreport:
			return

		if reportMode == ReportMode.HTML:
			if output is None:
				output = os.path.join(os.path.dirname(sys.modules["__main__"].__file__), os.path.basename(os.path.splitext(sys.modules["__main__"].__file__)[0] + "_PERF.html"))

			with open(output, "w") as f:
				#pylint: disable=missing-docstring
				class SharedLocals(object):
					identifiers = {}
					lastId = {}
					totalExc = 0
					totalCount = 0
					maxExcMean = 0
					maxIncMean = 0
					maxExcMax = 0
					maxExcMin = 0
					maxIncMax = 0
					maxIncMin = 0

				#pylint: disable=invalid-name
				def _getIdentifier(s):
					_,_,base = s.rpartition("::")
					if s not in SharedLocals.identifiers:
						SharedLocals.identifiers[s] = SharedLocals.lastId.setdefault(base, 0)
						SharedLocals.lastId[base] += 1
					return base + "\\x0b" * SharedLocals.identifiers[s]

				def _recurseHtml(report, sortedKeys, prefix, printed, itemfmt, indent):
					first = True
					for key in sortedKeys:
						if key in printed:
							continue

						if key.startswith(prefix):
							reportEntry = report[key]
							reportIncMean = reportEntry[Position.Inclusive] / reportEntry[Position.Count]
							reportExcMean = reportEntry[Position.Exclusive] / reportEntry[Position.Count]

							printkey = key.replace(prefix, "", 1)
							if printkey.find("::") != -1:
								continue
							if not first:
								f.write("\t" * (indent+1))
								f.write("],\n")
							f.write("\n")
							f.write("\t" * (indent+1))
							f.write(
								itemfmt.format(
									printkey,
									reportEntry[Position.Inclusive],
									reportEntry[Position.Exclusive],
									reportEntry[Position.Count],
									reportEntry[Position.MaxInc],
									reportEntry[Position.MinInc],
									reportIncMean,
									reportEntry[Position.MaxExc],
									reportEntry[Position.MinExc],
									reportExcMean,
								)
							)

							SharedLocals.totalExc += reportEntry[Position.Exclusive]
							SharedLocals.totalCount += reportEntry[Position.Count]
							SharedLocals.maxExcMean = max(SharedLocals.maxExcMean, reportExcMean)
							SharedLocals.maxIncMean = max(SharedLocals.maxIncMean, reportIncMean)
							SharedLocals.maxExcMax = max(SharedLocals.maxExcMax, reportEntry[Position.MaxExc])
							SharedLocals.maxIncMax = max(SharedLocals.maxIncMax, reportEntry[Position.MaxInc])
							SharedLocals.maxExcMin = max(SharedLocals.maxExcMin, reportEntry[Position.MinExc])
							SharedLocals.maxIncMin = max(SharedLocals.maxIncMin, reportEntry[Position.MinInc])

							f.write("\t" * (indent+2))
							f.write("[")
							printed.add(key)
							_recurseHtml(report, sortedKeys, key + "::", printed, itemfmt, indent + 2)
							first = False
					if not first:
						f.write("\t" * (indent+1))
						f.write("]\n")
						f.write("\t" * indent)
					f.write("]\n")

				def _printReportHtml(report, threadId):
					if not report:
						return
					totalcount = 0
					for key in report:
						totalcount += report[key][Position.Count]

					sortedKeys = sorted(report, reverse=True, key=lambda x: report[x][0] if reportMode == ReportMode.TREE else report[x][1])

					threadScriptId = threadId.replace(" ", "_")
					f.write(_blocks[0].format(threadScriptId, threadId))

					f.write("\t\t\t\t\t\t['<{}_root>', null, 0, 0 ],\n".format(threadScriptId))
					for key in sortedKeys:
						parent, _, thisKey = key.rpartition("::")
						ident = _getIdentifier(key)
						f.write("\t\t\t\t\t\t['" + ident + "', ")
						if parent:
							f.write("'" + _getIdentifier(parent) + "', ")
						else:
							f.write("'<{}_root>',".format(threadScriptId))
						f.write(str(report[key][0]))
						f.write(", ")
						f.write(str(report[key][0]))
						f.write("],\n")

						exclusiveIdent = _getIdentifier(key + "::<" +thisKey + ">")
						f.write("\t\t\t\t\t\t['" + exclusiveIdent + "', ")
						f.write("'" + ident + "', ")
						f.write(str(max(report[key][1], 0.0000000001)))
						f.write(", ")
						f.write(str(max(report[key][1], 0.0000000001)))
						f.write("],\n")

					f.write(_blocks[1].format(threadScriptId, threadId))

					itemfmt = "[ \"{}\", {}, {}, {}, {}, {}, {}, {}, {}, {},\n"
					printed = set()
					first = True
					for key in sortedKeys:
						reportEntry = report[key]
						reportIncMean = reportEntry[Position.Inclusive] / reportEntry[Position.Count]
						reportExcMean = reportEntry[Position.Exclusive] / reportEntry[Position.Count]

						if key in printed:
							continue
						if key.find("::") != -1:
							continue
						if not first:
							f.write("\t\t\t\t\t],\n")
						f.write("\t\t\t\t\t")
						f.write(
							itemfmt.format(
								key,
								reportEntry[Position.Inclusive],
								reportEntry[Position.Exclusive],
								reportEntry[Position.Count],
								reportEntry[Position.MaxInc],
								reportEntry[Position.MinInc],
								reportIncMean,
								reportEntry[Position.MaxExc],
								reportEntry[Position.MinExc],
								reportExcMean,
							)
						)

						SharedLocals.totalExc += reportEntry[Position.Exclusive]
						SharedLocals.totalCount += reportEntry[Position.Count]
						SharedLocals.maxExcMean = max(SharedLocals.maxExcMean, reportExcMean)
						SharedLocals.maxIncMean = max(SharedLocals.maxIncMean, reportIncMean)
						SharedLocals.maxExcMax = max(SharedLocals.maxExcMax, reportEntry[Position.MaxExc])
						SharedLocals.maxIncMax = max(SharedLocals.maxIncMax, reportEntry[Position.MaxInc])
						SharedLocals.maxExcMin = max(SharedLocals.maxExcMin, reportEntry[Position.MinExc])
						SharedLocals.maxIncMin = max(SharedLocals.maxIncMin, reportEntry[Position.MinInc])
						f.write("\t\t\t\t\t\t[")

						_recurseHtml(report, sortedKeys, key + "::", printed, itemfmt, 6)
						first = False

					f.write(
						"\t\t\t\t\t]"
						"\n\t\t\t\t]"
					)
					f.write("\n\t\t\t\tvar totals_{} = [{}, {}, {}, {}, {}, {}, {}, {}]\n".format(
						threadScriptId, SharedLocals.totalExc, SharedLocals.totalCount,
						SharedLocals.maxIncMax, SharedLocals.maxIncMin, SharedLocals.maxIncMean,
						SharedLocals.maxExcMax, SharedLocals.maxExcMin, SharedLocals.maxExcMean,
					))
					f.write(_blocks[2].format(threadScriptId, threadId))

				f.write(_htmlHeader.format(os.path.basename(sys.modules["__main__"].__file__)))

				for threadId, report in threadreports.items():
					if threadId == threading.current_thread().ident:
						continue

					_printReportHtml(report, "Worker Thread {}".format(threadId))

				_printReportHtml(threadreports[threading.current_thread().ident], "Main Thread")
				if len(threadreports) != 1:
					_printReportHtml(fullreport, "CUMULATIVE")

				f.write(_htmlFooter)

		else:
			if output is None:
				#pylint: disable=invalid-name,missing-docstring
				def printIt(*args, **kwargs):
					print(*args, **kwargs)
				output = printIt
			output("Perf reports:")

			def _recurse(report, sortedKeys, prefix, replacementText, printed, itemfmt):
				prev = (None, None)

				for key in sortedKeys:
					if key in printed:
						continue

					if key.startswith(prefix):
						printkey = key.replace(prefix, replacementText, 1)
						if printkey.find("::") != -1:
							continue
						if prev != (None, None):
							reportEntry = report[prev[1]]
							reportIncMean = reportEntry[Position.Inclusive] / reportEntry[Position.Count]
							reportExcMean = reportEntry[Position.Exclusive] / reportEntry[Position.Count]
							output(
								itemfmt.format(
									prev[0],
									_formatTime(reportEntry[Position.Inclusive]),
									_formatTime(reportEntry[Position.Exclusive]),
									reportEntry[Position.Count],
									_formatTime(reportEntry[Position.MinInc]),
									_formatTime(reportEntry[Position.MaxInc]),
									_formatTime(reportIncMean),
									_formatTime(reportEntry[Position.MinExc]),
									_formatTime(reportEntry[Position.MaxExc]),
									_formatTime(reportExcMean),
								)
							)
							printed.add(prev[1])
							_recurse(report, sortedKeys, prev[1] + "::", replacementText[:-4] + " \u2502  " + " \u251c\u2500 ", printed, itemfmt)
						prev = (printkey, key)

				if prev != (None, None):
					printkey = prev[0].replace("\u251c", "\u2514")
					reportEntry = report[prev[1]]
					reportIncMean = reportEntry[Position.Inclusive] / reportEntry[Position.Count]
					reportExcMean = reportEntry[Position.Exclusive] / reportEntry[Position.Count]
					output(
						itemfmt.format(
							printkey,
							_formatTime(reportEntry[Position.Inclusive]),
							_formatTime(reportEntry[Position.Exclusive]),
							reportEntry[Position.Count],
							_formatTime(reportEntry[Position.MinInc]),
							_formatTime(reportEntry[Position.MaxInc]),
							_formatTime(reportIncMean),
							_formatTime(reportEntry[Position.MinExc]),
							_formatTime(reportEntry[Position.MaxExc]),
							_formatTime(reportExcMean),
						)
					)
					printed.add(prev[1])
					_recurse(report, sortedKeys, prev[1] + "::", replacementText[:-4] + "    " + " \u251c\u2500 ", printed, itemfmt)

			def _alteredKey(key):
				return re.sub("([^:]*::)", "    ", key)

			def _printReport(report, threadId):
				if not report:
					return

				maxlen = len(str(threadId))
				totalcount = 0
				for key in report:
					maxlen = max(len(_alteredKey(key)), maxlen)
					totalcount += report[key][2]

				output("")
				linefmt = "+={{:=<{}}}=+============+============+===========+============+============+============+============+============+============+".format(maxlen)
				line = linefmt.format('')
				output(line)
				headerfmt = "| {{:<{}}} | INCLUSIVE  | EXCLUSIVE  |   CALLS   |  INC_MIN   |  INC_MAX   |  INC_MEAN  |  EXC_MIN   |  EXC_MAX   |  EXC_MEAN  |".format(maxlen)
				output(headerfmt.format(threadId))
				output(line)
				itemfmt = "| {{:{}}} | {{:>10}} | {{:>10}} | {{:>9}} | {{:>10}} | {{:>10}} | {{:>10}} | {{:>10}} | {{:>10}} | {{:>10}} |".format(maxlen)
				printed = set()
				sortedKeys = sorted(report, reverse=True, key=lambda x: report[x][0] if reportMode == ReportMode.TREE else report[x][1])
				total = 0
				for key in sortedKeys:
					if key in printed:
						continue
					if key.find("::") != -1:
						continue
					reportEntry = report[key]
					output(
						itemfmt.format(
							key,
							_formatTime(reportEntry[Position.Inclusive]),
							_formatTime(reportEntry[Position.Exclusive]),
							reportEntry[Position.Count],
							_formatTime(reportEntry[Position.MinInc]),
							_formatTime(reportEntry[Position.MaxInc]),
							_formatTime(reportEntry[Position.Inclusive] / report[key][Position.Count]),
							_formatTime(reportEntry[Position.MinExc]),
							_formatTime(reportEntry[Position.MaxExc]),
							_formatTime(reportEntry[Position.Exclusive] / report[key][Position.Count]),
						)
					)
					if reportMode == ReportMode.FLAT:
						total += reportEntry[Position.Exclusive]
					else:
						total += reportEntry[Position.Inclusive]
					_recurse(report, sortedKeys, key + "::", " \u251c\u2500 ", printed, itemfmt)

				output(line)

			for threadId, report in threadreports.items():
				if threadId == threading.current_thread().ident:
					continue

				_printReport(report, "Worker Thread {}".format(threadId))

			_printReport(threadreports[threading.current_thread().ident], "Main Thread")
			if len(threadreports) != 1:
				_printReport(fullreport, "CUMULATIVE")
